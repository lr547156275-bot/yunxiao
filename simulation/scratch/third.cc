/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License version 2 as
* published by the Free Software Foundation;
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/

#undef PGO_TRAINING
#define PATH_TO_PGO_CONFIG "path_to_pgo_config"

#include <iostream>
#include <fstream>
#include <unordered_map>
#include <time.h> 
#include "ns3/core-module.h"
#include "ns3/qbb-helper.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/global-route-manager.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/packet.h"
#include "ns3/error-model.h"
#include <ns3/rdma.h>
#include <ns3/rdma-client.h>
#include <ns3/rdma-client-helper.h>
#include <ns3/rdma-driver.h>
#include <ns3/switch-node.h>
#include <ns3/sim-setting.h>

using namespace ns3;
using namespace std;

NS_LOG_COMPONENT_DEFINE("GENERIC_SIMULATION");

uint32_t cc_mode = 1;//拥塞控制模式
bool enable_qcn = true, use_dynamic_pfc_threshold = true;//启用QCN，使用动态PFC阈值
uint32_t packet_payload_size = 1000, l2_chunk_size = 0, l2_ack_interval = 0;//数据包载荷大小；「L2 分块」大小，收到NACK时按chunk回退重传；0 表示关闭chunk模式；发ack的时间间隔
double pause_time = 5, simulator_stop_time = 3.01;//暂停时间，模拟器停止时间
std::string data_rate, link_delay, topology_file, flow_file, trace_file, trace_output_file;
std::string fct_output_file = "fct.txt";
std::string pfc_output_file = "pfc.txt";

double alpha_resume_interval = 55, rp_timer, ewma_gain = 1 / 16;//恢复间隔；在reaction阶段的时候多久做一次AI；EWMA增益
double rate_decrease_interval = 4;//速率降低间隔，也就是在降速的时候多久降速一次
uint32_t fast_recovery_times = 5;//快速恢复次数，也就是收到CNP后快速恢复阶段做几次加速
std::string rate_ai, rate_hai, min_rate = "100Mb/s";//速率AI，速率HAI，最小速率
std::string dctcp_rate_ai = "1000Mb/s";//DCTCP速率AI

bool clamp_target_rate = false, l2_back_to_zero = false;//连续降速时，是否锁定目标速率；DCQCN的ACK重传策略：go-back-0
double error_rate_per_link = 0.0;//每条链路的错误率
uint32_t has_win = 1;//是否有设置BDP窗口
uint32_t global_t = 1;//是否全局都用RTT_Max还是每条流自己的RTT
uint32_t mi_thresh = 5;//连续AI几次后进MI（乘性增速）
bool var_win = false, fast_react = true;//窗口是否随当前速率缩放；是否每一个ACK都快速反应，即DCQCN是否每一个ACK都提速，如果是否的话就是使用定时器/发送字节数批量提速
bool multi_rate = true;//多速率，也就是每一跳是否单独速率还是说聚合跳数的速率
bool sample_feedback = false;//采样反馈，也就是INT反馈是每个包都反馈还是采样
double pint_log_base = 1.05;//PINT对数量化底数
double pint_prob = 1.0;//PINT概率
double u_target = 0.95;//目标利用率
uint32_t int_multi = 1;//INT头里的qLen的量化倍数
bool rate_bound = true;//速率限制/即是否按照CC算出来的速率来限制nic发包速率

uint32_t ack_high_prio = 0;//设置ack为高优先级
uint64_t link_down_time = 0;//链路断开时间
uint32_t link_down_A = 0, link_down_B = 0;

uint32_t enable_trace = 1;//启用跟踪

uint32_t buffer_size = 16;//缓冲区大小

uint32_t qlen_dump_interval = 100000, qlen_mon_interval = 100;//队列长度dump间隔，队列长度监控间隔
uint64_t qlen_mon_start = 2000000000, qlen_mon_end = 2100000000;//队列长度监控开始时间，队列长度监控结束时间
string qlen_mon_file;

unordered_map<uint64_t, uint32_t> rate2kmax, rate2kmin;//这里设置的ECN是RED-ECN，也就是说这两个值是RED-ECN的阈值，当队列长度超过kmax时，触发ECN，当队列长度低于kmin时，不触发ECN
unordered_map<uint64_t, double> rate2pmax;//这个就是标记概率的最大值

/************************************************
 * Runtime varibles
 ***********************************************/
std::ifstream topof, flowf, tracef;

NodeContainer n;

uint64_t nic_rate;//网卡发送速率

uint64_t maxRtt, maxBdp;//最大RTT，最大BDP

struct Interface{//接口结构体
	uint32_t idx;//出接口编号
	bool up;//表示接口是否被拉起来了
	uint64_t delay;//延迟
	uint64_t bw;//带宽

	Interface() : idx(0), up(false){}//默认接口为0，默认接口下线状态为false
};

map<Ptr<Node>, map<Ptr<Node>, Interface> > nbr2if;//将node到邻居节点映射到interface即端口上
// Mapping destination to next hop for each node: <node, <dest, <nexthop0, ...> > >
map<Ptr<Node>, map<Ptr<Node>, vector<Ptr<Node> > > > nextHop;//映射表的吓一跳
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairDelay;//映射表的delay等等的属性，如果是路由阶段的话，pairdelay这些被取出放入新建表中开始累加
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairTxDelay;
map<uint32_t, map<uint32_t, uint64_t> > pairBw;
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairBdp;
map<uint32_t, map<uint32_t, uint64_t> > pairRtt;

std::vector<Ipv4Address> serverAddress;

// maintain port number for each host pair
std::unordered_map<uint32_t, unordered_map<uint32_t, uint16_t> > portNumder;

struct FlowInput{
	uint32_t src, dst, pg, maxPacketCount, port, dport;
	double start_time;
	uint32_t idx;
};//建立流
FlowInput flow_input = {0};//初始化
uint32_t flow_num;

void ReadFlowInput(){
	if (flow_input.idx < flow_num){
		flowf >> flow_input.src >> flow_input.dst >> flow_input.pg >> flow_input.dport >> flow_input.maxPacketCount >> flow_input.start_time;
		NS_ASSERT(n.Get(flow_input.src)->GetNodeType() == 0 && n.Get(flow_input.dst)->GetNodeType() == 0);
	}
}//读取flow.txt文件中的flow特征
void ScheduleFlowInputs(){//开始规划流
	while (flow_input.idx < flow_num && Seconds(flow_input.start_time) == Simulator::Now()){//开始执行流
		uint32_t port = portNumder[flow_input.src][flow_input.dst]++; // get a new port number 
		RdmaClientHelper clientHelper(flow_input.pg, serverAddress[flow_input.src], serverAddress[flow_input.dst], port, flow_input.dport, flow_input.maxPacketCount, has_win?(global_t==1?maxBdp:pairBdp[n.Get(flow_input.src)][n.Get(flow_input.dst)]):0, global_t==1?maxRtt:pairRtt[flow_input.src][flow_input.dst]);
		//这个里面传输的参数就是client的一些特征，pg是优先级组，maxPacketCoun是发送出去的总字节，其他的好理解
		ApplicationContainer appCon = clientHelper.Install(n.Get(flow_input.src));//在install后会在源host上建立一个QP（怎么建立的可以去看文件rdma-client.cc中的void RdmaClient）
		appCon.Start(Time(0));

		// get the next flow input
		flow_input.idx++;
		ReadFlowInput();//也就是说按仿真时间一条条启动，不是一次性启动的
	}

	// schedule the next time to run this function
	if (flow_input.idx < flow_num){
		Simulator::Schedule(Seconds(flow_input.start_time)-Simulator::Now(), ScheduleFlowInputs);
	}else { // no more flows, close the file
		flowf.close();
	}
}

Ipv4Address node_id_to_ip(uint32_t id){
	return Ipv4Address(0x0b000001 + ((id / 256) * 0x00010000) + ((id % 256) * 0x00000100));
}

uint32_t ip_to_node_id(Ipv4Address ip){
	return (ip.Get() >> 8) & 0xffff;
}

void qp_finish(FILE* fout, Ptr<RdmaQueuePair> q){//一条流/QP发完之后的收尾回调，记录FCT,写结果，清除状态
	uint32_t sid = ip_to_node_id(q->sip), did = ip_to_node_id(q->dip);//从QP的五元组IP反查node ip/一个源节点一个目标节点
	uint64_t base_rtt = pairRtt[sid][did], b = pairBw[sid][did];//第一个base_rtt是这对host的无拥塞往返时延；第二b是路径瓶颈带宽
	uint32_t total_bytes = q->m_size + ((q->m_size-1) / packet_payload_size + 1) * (CustomHeader::GetStaticWholeHeaderSize() - IntHeader::GetStaticSize()); // translate to the minimum bytes required (with header but no INT)
	//m_size为流大小，total_bytes是理想FCT下线上总字节数：payload总大小+头部开销大小（去掉Int(HPCC算法本身在头部添加的)，向上取整
	uint64_t standalone_fct = base_rtt + total_bytes * 8000000000lu / b;
	//理想状态下的FCT（即无排队，无拥塞）
	// sip, dip, sport, dport, size (B), start_time, fct (ns), standalone_fct (ns)
	fprintf(fout, "%08x %08x %u %u %lu %lu %lu %lu\n", q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->m_size, q->startTime.GetTimeStep(), (Simulator::Now() - q->startTime).GetTimeStep(), standalone_fct);
	fflush(fout);
	//清空文件

	// remove rxQp from the receiver
	Ptr<Node> dstNode = n.Get(did);
	Ptr<RdmaDriver> rdma = dstNode->GetObject<RdmaDriver> ();//创建对端dstnode对象指针
	rdma->m_rdma->DeleteRxQp(q->sip.Get(), q->m_pg, q->sport);//删除对端该QP的状态信息
}

void get_pfc(FILE* fout, Ptr<QbbNetDevice> dev, uint32_t type){
	fprintf(fout, "%lu %u %u %u %u\n", Simulator::Now().GetTimeStep(), dev->GetNode()->GetId(), dev->GetNode()->GetNodeType(), dev->GetIfIndex(), type);
}//记录PFC事件日志

struct QlenDistribution{
	vector<uint32_t> cnt; // cnt[i] is the number of times that the queue len is i KB

	void add(uint32_t qlen){
		uint32_t kb = qlen / 1000;
		if (cnt.size() < kb+1)
			cnt.resize(kb+1);
		cnt[kb]++;
	}
};//队列长度分布统计，这里传进来的qlen是字节数，然后这个kb就是把字节分桶成KB桶，模拟bucket。
map<uint32_t, map<uint32_t, QlenDistribution> > queue_result;//定义一个全局统计表，即queue_result[交换机ID][端口ID] = 这个端口的队列长度分布统计
void monitor_buffer(FILE* qlen_output, NodeContainer *n){
	for (uint32_t i = 0; i < n->GetN(); i++){
		if (n->Get(i)->GetNodeType() == 1){ // 判断这个node是不是交换机
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n->Get(i));//创建并继承一个交换机节点类的智能指针
			if (queue_result.find(i) == queue_result.end())//检查queue_result中有没有交换机i的记录
				queue_result[i];//如果没有就创建一个
			for (uint32_t j = 1; j < sw->GetNDevices(); j++){//遍历这个交换机上所有的网卡，因为大多数数据网卡都不会放在0上，所以从1开始
				uint32_t size = 0;//统计这个窗口的总排队字节数
				for (uint32_t k = 0; k < SwitchMmu::qCnt; k++)
					size += sw->m_mmu->egress_bytes[j][k];//遍历这个端口所有优先级队列，switchmmu：：qcnt是指的队列数量
				queue_result[i][j].add(size);
			}
		}
	}
	if (Simulator::Now().GetTimeStep() % qlen_dump_interval == 0){//判断是否要将统计结果写入
		fprintf(qlen_output, "time: %lu\n", Simulator::Now().GetTimeStep());
		for (auto &it0 : queue_result)//遍历所有已经统计过的交换机，其中it0.first是交换机id，it0.second是交换机下面的端口map
			for (auto &it1 : it0.second){//遍历这两个交换机的统计
				fprintf(qlen_output, "%u %u", it0.first, it1.first);
				auto &dist = it1.second.cnt;//交换机端口下的长度分布数组
				for (uint32_t i = 0; i < dist.size(); i++)
					fprintf(qlen_output, " %u", dist[i]);
				fprintf(qlen_output, "\n");
			}//再按照bucket写入
		fflush(qlen_output);
	}
	if (Simulator::Now().GetTimeStep() < qlen_mon_end)//这上面说明还没到监控结束时间
		Simulator::Schedule(NanoSeconds(qlen_mon_interval), &monitor_buffer, qlen_output, n);//然后周期性监控
}

void CalculateRoute(Ptr<Node> host){//以host为节点，计算所有节点往这个host的最短路径
	// queue for the BFS.
	vector<Ptr<Node> > q;//队列
	// Distance from the host to each node.
	map<Ptr<Node>, int> dis;//hop
	map<Ptr<Node>, uint64_t> delay;//链路传播延迟
	map<Ptr<Node>, uint64_t> txDelay;//发送延迟
	map<Ptr<Node>, uint64_t> bw;//瓶颈带宽
	// init BFS.
	q.push_back(host);
	dis[host] = 0;
	delay[host] = 0;
	txDelay[host] = 0;
	bw[host] = 0xfffffffffffffffflu;
	// BFS.
	for (int i = 0; i < (int)q.size(); i++){
		Ptr<Node> now = q[i];
		int d = dis[now];
		for (auto it = nbr2if[now].begin(); it != nbr2if[now].end(); it++){
			if (!it->second.up)//如果这个某个邻居节点的端口没有up则跳过
				continue;
			Ptr<Node> next = it->first;//记录下一跳的节点id
			if (dis.find(next) == dis.end()){//如果是第一次访问下一跳；在c++里find函数要是找不到key则会返回end()
				dis[next] = d + 1;//hop + 1
				delay[next] = delay[now] + it->second.delay;//添加链路的传播时延
				txDelay[next] = txDelay[now] + packet_payload_size * 1000000000lu * 8 / it->second.bw;//计算发送时延:数据大小bit/链路速率bit/s
				bw[next] = std::min(bw[now], it->second.bw);//瓶颈带宽
				// we only enqueue switch, because we do not want packets to go through host as middle point
				if (next->GetNodeType() == 1)//也就是说不希望中间的中转节点是host节点，一定得是switch
					q.push_back(next);
			}
			//如果now是next到host的某条最短路径上的下一跳，那就记录：next要去host，可以下一跳走now
			if (d + 1 == dis[next]){
				nextHop[next][host].push_back(now);
			}
		}
	}
		// nextHop[next][host].push_back(now) records that now is a valid
		// next hop for next when routing toward host.
	for (auto it : delay)
		pairDelay[it.first][host] = it.second;
	for (auto it : txDelay)
		pairTxDelay[it.first][host] = it.second;
	for (auto it : bw)
		pairBw[it.first->GetId()][host->GetId()] = it.second;
}//保存本轮的结果

void CalculateRoutes(NodeContainer &n){
	for (int i = 0; i < (int)n.GetN(); i++){
		Ptr<Node> node = n.Get(i);
		if (node->GetNodeType() == 0)
			CalculateRoute(node);
	}
}//遍历所有主机节点

void SetRoutingEntries(){
	//	nextHop[src-node][dst-node] = {nextHop}
	for (auto i = nextHop.begin(); i != nextHop.end(); i++){
		Ptr<Node> node = i->first;//fist指向的是源节点
		auto &table = i->second;//second指向的是dst节点
		for (auto j = table.begin(); j != table.end(); j++){//遍历当前node到所有dst的路由
			Ptr<Node> dst = j->first;//取每一个dst的node
			Ipv4Address dstAddr = dst->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();//接着取ip
			// The next hops towards the dst.
			vector<Ptr<Node> > nexts = j->second;//取下一跳
			for (int k = 0; k < (int)nexts.size(); k++){
				Ptr<Node> next = nexts[k];//遍历每一个下一跳，因为ECMP，所有存在等价路径
				uint32_t interface = nbr2if[node][next].idx;//取得从node到next这条链路中node这一侧的interface即三层接口
				//上面这个的作用就是将下一跳和出发节点的端口绑定
				if (node->GetNodeType() == 1)//如果是交换机则写入交换机路由表，如果host则写入host路由表
					DynamicCast<SwitchNode>(node)->AddTableEntry(dstAddr, interface);
				else{
					node->GetObject<RdmaDriver>()->m_rdma->AddTableEntry(dstAddr, interface);
				}
			}
		}
	}
}

// take down the link between a and b, and redo the routing
void TakeDownLink(NodeContainer n, Ptr<Node> a, Ptr<Node> b){
	if (!nbr2if[a][b].up)//如果传入的这两个节点的连接并没有up则返回null
		return;
	// take down link between a and b
	nbr2if[a][b].up = nbr2if[b][a].up = false;//双边链路全部关闭
	nextHop.clear();//清除下一跳关系并重新计算路由
	CalculateRoutes(n);
	for (uint32_t i = 0; i < n.GetN(); i++){//清空所有节点当前以及安装的路由表
		if (n.Get(i)->GetNodeType() == 1)
			DynamicCast<SwitchNode>(n.Get(i))->ClearTable();
		else
			n.Get(i)->GetObject<RdmaDriver>()->m_rdma->ClearTable();
	}
	DynamicCast<QbbNetDevice>(a->GetDevice(nbr2if[a][b].idx))->TakeDown();
	DynamicCast<QbbNetDevice>(b->GetDevice(nbr2if[b][a].idx))->TakeDown();//关闭两边的网卡
	// reset routing table
	SetRoutingEntries();//将刚刚新得到的路由表安装到node上

	// redistribute qp on each host
	for (uint32_t i = 0; i < n.GetN(); i++){
		if (n.Get(i)->GetNodeType() == 0)//找到host节点
			n.Get(i)->GetObject<RdmaDriver>()->m_rdma->RedistributeQp();
			//重新创造QPQ；在RedistributeQp这个函数中：1.clear了原来每个NIC上的QP分组；2.对原来每一个已有QP重新根据当前QP选择NIC，再加入NIC队列，并通知QP已经重新分配
	}
}

uint64_t get_nic_rate(NodeContainer &n){
	for (uint32_t i = 0; i < n.GetN(); i++)
		if (n.Get(i)->GetNodeType() == 0)//找到主机节点，返回它的device1的链路速率
			return DynamicCast<QbbNetDevice>(n.Get(i)->GetDevice(1))->GetDataRate().GetBitRate();
}

int main(int argc, char *argv[])
{
	clock_t begint, endt;//记录运行耗时
	begint = clock();
#ifndef PGO_TRAINING
	if (argc > 1)
#else
	if (true)
#endif//判断是否有指定配置文件
	{
		//Read the configuration file
		std::ifstream conf;
#ifndef PGO_TRAINING
		conf.open(argv[1]);
#else
		conf.open(PATH_TO_PGO_CONFIG);
#endif
		while (!conf.eof())//是否文件末尾
		{
			std::string key;
			conf >> key;

			//std::cout << conf.cur << "\n";

			if (key.compare("ENABLE_QCN") == 0)//QCN是否打开
			{
				uint32_t v;
				conf >> v;
				enable_qcn = v;
				if (enable_qcn)
					std::cout << "ENABLE_QCN\t\t\t" << "Yes" << "\n";
				else
					std::cout << "ENABLE_QCN\t\t\t" << "No" << "\n";
			}
			else if (key.compare("USE_DYNAMIC_PFC_THRESHOLD") == 0)
			{
				uint32_t v;
				conf >> v;
				use_dynamic_pfc_threshold = v;
				if (use_dynamic_pfc_threshold)
					std::cout << "USE_DYNAMIC_PFC_THRESHOLD\t" << "Yes" << "\n";
				else
					std::cout << "USE_DYNAMIC_PFC_THRESHOLD\t" << "No" << "\n";
			}
			else if (key.compare("CLAMP_TARGET_RATE") == 0)
			{
				uint32_t v;
				conf >> v;
				clamp_target_rate = v;
				if (clamp_target_rate)
					std::cout << "CLAMP_TARGET_RATE\t\t" << "Yes" << "\n";
				else
					std::cout << "CLAMP_TARGET_RATE\t\t" << "No" << "\n";
			}
			else if (key.compare("PAUSE_TIME") == 0)
			{
				double v;
				conf >> v;
				pause_time = v;
				std::cout << "PAUSE_TIME\t\t\t" << pause_time << "\n";
			}
			else if (key.compare("DATA_RATE") == 0)
			{
				std::string v;
				conf >> v;
				data_rate = v;
				std::cout << "DATA_RATE\t\t\t" << data_rate << "\n";
			}
			else if (key.compare("LINK_DELAY") == 0)
			{
				std::string v;
				conf >> v;
				link_delay = v;
				std::cout << "LINK_DELAY\t\t\t" << link_delay << "\n";
			}
			else if (key.compare("PACKET_PAYLOAD_SIZE") == 0)
			{
				uint32_t v;
				conf >> v;
				packet_payload_size = v;
				std::cout << "PACKET_PAYLOAD_SIZE\t\t" << packet_payload_size << "\n";
			}
			else if (key.compare("L2_CHUNK_SIZE") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_chunk_size = v;
				std::cout << "L2_CHUNK_SIZE\t\t\t" << l2_chunk_size << "\n";
			}
			else if (key.compare("L2_ACK_INTERVAL") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_ack_interval = v;
				std::cout << "L2_ACK_INTERVAL\t\t\t" << l2_ack_interval << "\n";
			}
			else if (key.compare("L2_BACK_TO_ZERO") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_back_to_zero = v;
				if (l2_back_to_zero)
					std::cout << "L2_BACK_TO_ZERO\t\t\t" << "Yes" << "\n";
				else
					std::cout << "L2_BACK_TO_ZERO\t\t\t" << "No" << "\n";
			}
			else if (key.compare("TOPOLOGY_FILE") == 0)
			{
				std::string v;
				conf >> v;
				topology_file = v;
				std::cout << "TOPOLOGY_FILE\t\t\t" << topology_file << "\n";
			}
			else if (key.compare("FLOW_FILE") == 0)
			{
				std::string v;
				conf >> v;
				flow_file = v;
				std::cout << "FLOW_FILE\t\t\t" << flow_file << "\n";
			}
			else if (key.compare("TRACE_FILE") == 0)
			{
				std::string v;
				conf >> v;
				trace_file = v;
				std::cout << "TRACE_FILE\t\t\t" << trace_file << "\n";
			}
			else if (key.compare("TRACE_OUTPUT_FILE") == 0)
			{
				std::string v;
				conf >> v;
				trace_output_file = v;
				if (argc > 2)
				{
					trace_output_file = trace_output_file + std::string(argv[2]);
				}
				std::cout << "TRACE_OUTPUT_FILE\t\t" << trace_output_file << "\n";
			}
			else if (key.compare("SIMULATOR_STOP_TIME") == 0)
			{
				double v;
				conf >> v;
				simulator_stop_time = v;
				std::cout << "SIMULATOR_STOP_TIME\t\t" << simulator_stop_time << "\n";
			}
			else if (key.compare("ALPHA_RESUME_INTERVAL") == 0)
			{
				double v;
				conf >> v;
				alpha_resume_interval = v;
				std::cout << "ALPHA_RESUME_INTERVAL\t\t" << alpha_resume_interval << "\n";
			}
			else if (key.compare("RP_TIMER") == 0)
			{
				double v;
				conf >> v;
				rp_timer = v;
				std::cout << "RP_TIMER\t\t\t" << rp_timer << "\n";
			}
			else if (key.compare("EWMA_GAIN") == 0)
			{
				double v;
				conf >> v;
				ewma_gain = v;
				std::cout << "EWMA_GAIN\t\t\t" << ewma_gain << "\n";
			}
			else if (key.compare("FAST_RECOVERY_TIMES") == 0)
			{
				uint32_t v;
				conf >> v;
				fast_recovery_times = v;
				std::cout << "FAST_RECOVERY_TIMES\t\t" << fast_recovery_times << "\n";
			}
			else if (key.compare("RATE_AI") == 0)
			{
				std::string v;
				conf >> v;
				rate_ai = v;
				std::cout << "RATE_AI\t\t\t\t" << rate_ai << "\n";
			}
			else if (key.compare("RATE_HAI") == 0)
			{
				std::string v;
				conf >> v;
				rate_hai = v;
				std::cout << "RATE_HAI\t\t\t" << rate_hai << "\n";
			}
			else if (key.compare("ERROR_RATE_PER_LINK") == 0)
			{
				double v;
				conf >> v;
				error_rate_per_link = v;
				std::cout << "ERROR_RATE_PER_LINK\t\t" << error_rate_per_link << "\n";
			}
			else if (key.compare("CC_MODE") == 0){
				conf >> cc_mode;
				std::cout << "CC_MODE\t\t" << cc_mode << '\n';
			}else if (key.compare("RATE_DECREASE_INTERVAL") == 0){
				double v;
				conf >> v;
				rate_decrease_interval = v;
				std::cout << "RATE_DECREASE_INTERVAL\t\t" << rate_decrease_interval << "\n";
			}else if (key.compare("MIN_RATE") == 0){
				conf >> min_rate;
				std::cout << "MIN_RATE\t\t" << min_rate << "\n";
			}else if (key.compare("FCT_OUTPUT_FILE") == 0){
				conf >> fct_output_file;
				std::cout << "FCT_OUTPUT_FILE\t\t" << fct_output_file << '\n';
			}else if (key.compare("HAS_WIN") == 0){
				conf >> has_win;
				std::cout << "HAS_WIN\t\t" << has_win << "\n";
			}else if (key.compare("GLOBAL_T") == 0){
				conf >> global_t;
				std::cout << "GLOBAL_T\t\t" << global_t << '\n';
			}else if (key.compare("MI_THRESH") == 0){
				conf >> mi_thresh;
				std::cout << "MI_THRESH\t\t" << mi_thresh << '\n';
			}else if (key.compare("VAR_WIN") == 0){
				uint32_t v;
				conf >> v;
				var_win = v;
				std::cout << "VAR_WIN\t\t" << v << '\n';
			}else if (key.compare("FAST_REACT") == 0){
				uint32_t v;
				conf >> v;
				fast_react = v;
				std::cout << "FAST_REACT\t\t" << v << '\n';
			}else if (key.compare("U_TARGET") == 0){
				conf >> u_target;
				std::cout << "U_TARGET\t\t" << u_target << '\n';
			}else if (key.compare("INT_MULTI") == 0){
				conf >> int_multi;
				std::cout << "INT_MULTI\t\t\t\t" << int_multi << '\n';
			}else if (key.compare("RATE_BOUND") == 0){
				uint32_t v;
				conf >> v;
				rate_bound = v;
				std::cout << "RATE_BOUND\t\t" << rate_bound << '\n';
			}else if (key.compare("ACK_HIGH_PRIO") == 0){
				conf >> ack_high_prio;
				std::cout << "ACK_HIGH_PRIO\t\t" << ack_high_prio << '\n';
			}else if (key.compare("DCTCP_RATE_AI") == 0){
				conf >> dctcp_rate_ai;
				std::cout << "DCTCP_RATE_AI\t\t\t\t" << dctcp_rate_ai << "\n";
			}else if (key.compare("PFC_OUTPUT_FILE") == 0){
				conf >> pfc_output_file;
				std::cout << "PFC_OUTPUT_FILE\t\t\t\t" << pfc_output_file << '\n';
			}else if (key.compare("LINK_DOWN") == 0){
				conf >> link_down_time >> link_down_A >> link_down_B;
				std::cout << "LINK_DOWN\t\t\t\t" << link_down_time << ' '<< link_down_A << ' ' << link_down_B << '\n';
			}else if (key.compare("ENABLE_TRACE") == 0){
				conf >> enable_trace;
				std::cout << "ENABLE_TRACE\t\t\t\t" << enable_trace << '\n';
			}else if (key.compare("KMAX_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "KMAX_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					uint32_t k;
					conf >> rate >> k;
					rate2kmax[rate] = k;
					std::cout << ' ' << rate << ' ' << k;
				}
				std::cout<<'\n';
			}else if (key.compare("KMIN_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "KMIN_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					uint32_t k;
					conf >> rate >> k;
					rate2kmin[rate] = k;
					std::cout << ' ' << rate << ' ' << k;
				}
				std::cout<<'\n';
			}else if (key.compare("PMAX_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "PMAX_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					double p;
					conf >> rate >> p;
					rate2pmax[rate] = p;
					std::cout << ' ' << rate << ' ' << p;
				}
				std::cout<<'\n';
			}else if (key.compare("BUFFER_SIZE") == 0){
				conf >> buffer_size;
				std::cout << "BUFFER_SIZE\t\t\t\t" << buffer_size << '\n';
			}else if (key.compare("QLEN_MON_FILE") == 0){
				conf >> qlen_mon_file;
				std::cout << "QLEN_MON_FILE\t\t\t\t" << qlen_mon_file << '\n';
			}else if (key.compare("QLEN_MON_START") == 0){
				conf >> qlen_mon_start;
				std::cout << "QLEN_MON_START\t\t\t\t" << qlen_mon_start << '\n';
			}else if (key.compare("QLEN_MON_END") == 0){
				conf >> qlen_mon_end;
				std::cout << "QLEN_MON_END\t\t\t\t" << qlen_mon_end << '\n';
			}else if (key.compare("MULTI_RATE") == 0){
				int v;
				conf >> v;
				multi_rate = v;
				std::cout << "MULTI_RATE\t\t\t\t" << multi_rate << '\n';
			}else if (key.compare("SAMPLE_FEEDBACK") == 0){
				int v;
				conf >> v;
				sample_feedback = v;
				std::cout << "SAMPLE_FEEDBACK\t\t\t\t" << sample_feedback << '\n';
			}else if(key.compare("PINT_LOG_BASE") == 0){
				conf >> pint_log_base;
				std::cout << "PINT_LOG_BASE\t\t\t\t" << pint_log_base << '\n';
			}else if (key.compare("PINT_PROB") == 0){
				conf >> pint_prob;
				std::cout << "PINT_PROB\t\t\t\t" << pint_prob << '\n';
			}
			fflush(stdout);
		}
		conf.close();//关闭配置文件
	}
	else//若是没写配置文件但是又PGO_TRAINING
	{
		std::cout << "Error: require a config file\n";
		fflush(stdout);
		return 1;
	}


	bool dynamicth = use_dynamic_pfc_threshold;//将全局变量转成一个bool

	Config::SetDefault("ns3::QbbNetDevice::PauseTime", UintegerValue(pause_time));//设置PFC暂停时间
	Config::SetDefault("ns3::QbbNetDevice::QcnEnabled", BooleanValue(enable_qcn));//配置是否启用QCN
	Config::SetDefault("ns3::QbbNetDevice::DynamicThreshold", BooleanValue(dynamicth));//配置是否使用动态PFC阈值

	// set int_multi
	IntHop::multi = int_multi;//HPCC算法中IntHop指的是INT每跳信息结构。里面包含每个交换机hop的一些状态
	// IntHeader::mode，这边就是根据拥塞模式选择IntHeader的格式，比如mode==7，也就是timely模式，主要是基于RTT，所以内部放一个时间戳TS
	if (cc_mode == 7) // timely, use ts
		IntHeader::mode = IntHeader::TS;
	else if (cc_mode == 3) // hpcc, use int，普通模式，会往里面写入当前一跳的链路状态：比如说时间，端口发送的字节计数，该设备长度和链路速率
		IntHeader::mode = IntHeader::NORMAL;
	else if (cc_mode == 10) // hpcc-pint，往头部加入压缩的字段
		IntHeader::mode = IntHeader::PINT;
	else // others, no extra header，不添加额外头
		IntHeader::mode = IntHeader::NONE;

	// Set Pint
	if (cc_mode == 10){
		Pint::set_log_base(pint_log_base);//设置对数量化底数，也就是上面配置的，用意就是将网络负载什么的信息编码成一个较小的整数，底数越接近1，需要的bit越多
		IntHeader::pint_bytes = Pint::get_n_bytes();//计算占用的字节bit
		printf("PINT bits: %d bytes: %d\n", Pint::get_n_bits(), Pint::get_n_bytes());
	}

	//SeedManager::SetSeed(time(NULL));

	topof.open(topology_file.c_str());
	flowf.open(flow_file.c_str());
	tracef.open(trace_file.c_str());
	uint32_t node_num, switch_num, link_num, trace_num;
	topof >> node_num >> switch_num >> link_num;
	flowf >> flow_num;
	tracef >> trace_num;


	//n.Create(node_num);
	//在拓扑中读取数据在创建节点，比如说开头是5 3 4，意思是5个节点，3个switch，4条链路
	std::vector<uint32_t> node_type(node_num, 0);//创建一个长度为node_num的数组，初始化为0
	for (uint32_t i = 0; i < switch_num; i++)
	{
		uint32_t sid;
		topof >> sid;
		node_type[sid] = 1;
	}
	for (uint32_t i = 0; i < node_num; i++){
		if (node_type[i] == 0)//创建主机host
			n.Add(CreateObject<Node>());
		else{//创建switch
			Ptr<SwitchNode> sw = CreateObject<SwitchNode>();
			n.Add(sw);
			sw->SetAttribute("EcnEnabled", BooleanValue(enable_qcn));//switch中是否打开QCN
		}
	}


	NS_LOG_INFO("Create nodes.");

	InternetStackHelper internet;
	internet.Install(n);

	//
	// Assign IP to each server
	//
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 0){ // is server
			serverAddress.resize(i + 1);
			serverAddress[i] = node_id_to_ip(i);
		}
	}

	NS_LOG_INFO("Create channels.");

	//
	// Explicitly create the channels required by the topology.
	//

	Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();//错误模型，作用是让包按一定概率被认为楚错丢掉，控制丢包率
	Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();//均匀随机数发生器
	rem->SetRandomVariable(uv);//将生成的随机数交给错误模型使用，也就是说后面每一个包是否出错会通过这个随机数模型决定
	uv->SetStream(50);//随机数编号，即若是上述出错率为0.1，随机数 < 0.1那这样包就会出错，反之正常
	rem->SetAttribute("ErrorRate", DoubleValue(error_rate_per_link));//设置错误率
	rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));//设置错误单位，按照bit来

	FILE *pfc_file = fopen(pfc_output_file.c_str(), "w");

	QbbHelper qbb;//这个Helper用来创建NetDevice，Channel，队列，还有PFC/QCN相关功能，意思差不多就是安装了一个Qbb队列，所以Qbb差不多就是一个支持很多功能的网卡链路模型
	Ipv4AddressHelper ipv4;
	for (uint32_t i = 0; i < link_num; i++)//开始构造链路
	{
		uint32_t src, dst;//读取一条链路
		std::string data_rate, link_delay;//链路速率，传播时延，包错误率
		double error_rate;
		topof >> src >> dst >> data_rate >> link_delay >> error_rate;

		Ptr<Node> snode = n.Get(src), dnode = n.Get(dst);

		qbb.SetDeviceAttribute("DataRate", StringValue(data_rate));
		qbb.SetChannelAttribute("Delay", StringValue(link_delay));

		if (error_rate > 0)//配置错误模型
		{
			Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();
			Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();
			rem->SetRandomVariable(uv);
			uv->SetStream(50);
			rem->SetAttribute("ErrorRate", DoubleValue(error_rate));
			rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));
			qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
		}
		else//也就是说内部这个error_rate是一个局部变量，如果局部变量为0，则使用在for之前的时候创建的那个全局变量的概率
		{
			qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
		}

		fflush(stdout);

		// Assigne server IP
		// Note: this should be before the automatic assignment below (ipv4.Assign(d)),
		// because we want our IP to be the primary IP (first in the IP address list),
		// so that the global routing is based on our IP
		NetDeviceContainer d = qbb.Install(snode, dnode);//安装链路
		if (snode->GetNodeType() == 0){
			Ptr<Ipv4> ipv4 = snode->GetObject<Ipv4>();
			ipv4->AddInterface(d.Get(0));
			ipv4->AddAddress(1, Ipv4InterfaceAddress(serverAddress[src], Ipv4Mask(0xff000000)));
		}
		if (dnode->GetNodeType() == 0){
			Ptr<Ipv4> ipv4 = dnode->GetObject<Ipv4>();
			ipv4->AddInterface(d.Get(1));
			ipv4->AddAddress(1, Ipv4InterfaceAddress(serverAddress[dst], Ipv4Mask(0xff000000)));
		}

		//给这两个节点设置IP（serverAddress[i] = node_id_to_ip(i);）

		// used to create a graph of the topology
		nbr2if[snode][dnode].idx = DynamicCast<QbbNetDevice>(d.Get(0))->GetIfIndex();
		nbr2if[snode][dnode].up = true;
		nbr2if[snode][dnode].delay = DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(0))->GetChannel())->GetDelay().GetTimeStep();
		nbr2if[snode][dnode].bw = DynamicCast<QbbNetDevice>(d.Get(0))->GetDataRate().GetBitRate();
		nbr2if[dnode][snode].idx = DynamicCast<QbbNetDevice>(d.Get(1))->GetIfIndex();
		nbr2if[dnode][snode].up = true;
		nbr2if[dnode][snode].delay = DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(1))->GetChannel())->GetDelay().GetTimeStep();
		nbr2if[dnode][snode].bw = DynamicCast<QbbNetDevice>(d.Get(1))->GetDataRate().GetBitRate();
		//建立拓扑邻接表的信息
		// This is just to set up the connectivity between nodes. The IP addresses are useless
		char ipstring[16];
		sprintf(ipstring, "10.%d.%d.0", i / 254 + 1, i % 254 + 1);
		ipv4.SetBase(ipstring, "255.255.255.0");
		ipv4.Assign(d);
		//给这条链路分配普通IP即不同的/24网段

		// setup PFC trace
		DynamicCast<QbbNetDevice>(d.Get(0))->TraceConnectWithoutContext("QbbPfc", MakeBoundCallback (&get_pfc, pfc_file, DynamicCast<QbbNetDevice>(d.Get(0))));
		//这个表示当d.Get(0)这个QbbNetDevice触发QbbPfc trace事件的时候调用get_pfc函数，然后写入pfc_file这里，下面的则是这条链路另外一端如果触发也一样写入
		DynamicCast<QbbNetDevice>(d.Get(1))->TraceConnectWithoutContext("QbbPfc", MakeBoundCallback (&get_pfc, pfc_file, DynamicCast<QbbNetDevice>(d.Get(1))));
	}
		// The simulation uses host serverAddress values for RDMA flows and
		// separate 10.x.x.0/24 addresses for point-to-point connectivity.
	nic_rate = get_nic_rate(n);

	// config switch
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 1){ // is switch
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));//把普通的node指针转化成switch指针
			uint32_t shift = 3; // 设置PFC动态阈值的超参数alpha
			for (uint32_t j = 1; j < sw->GetNDevices(); j++){//遍历switch上所有真实的端口
				Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(sw->GetDevice(j));//给端口创建网卡
				// 配置ECN
				uint64_t rate = dev->GetDataRate().GetBitRate();
				NS_ASSERT_MSG(rate2kmin.find(rate) != rate2kmin.end(), "must set kmin for each link speed");
				NS_ASSERT_MSG(rate2kmax.find(rate) != rate2kmax.end(), "must set kmax for each link speed");
				NS_ASSERT_MSG(rate2pmax.find(rate) != rate2pmax.end(), "must set pmax for each link speed");
				sw->m_mmu->ConfigEcn(j, rate2kmin[rate], rate2kmax[rate], rate2pmax[rate]);//将上面的那些参数写入switch MMU中
				// 配置PFC
				uint64_t delay = DynamicCast<QbbChannel>(dev->GetChannel())->GetDelay().GetTimeStep();//取出这个网卡连接的channel的delay
				uint32_t headroom = rate * delay / 8 / 1000000000 * 3;//配置headroom，所以headroom ≈ 3 * 带宽 * 单向传播时延；增益带宽时延积
				sw->m_mmu->ConfigHdrm(j, headroom);//写入

				// set pfc alpha, proportional to link bw
				sw->m_mmu->pfc_a_shift[j] = shift;//即2的三次方=8；故threshold阈值 = 剩余共享 buffer / 8
				while (rate > nic_rate && sw->m_mmu->pfc_a_shift[j] > 0){//当NIC速率大于host速率则开始减少shift这个参数，nic速率也要减半
					sw->m_mmu->pfc_a_shift[j]--;
					rate /= 2;
				}
			}
			sw->m_mmu->ConfigNPort(sw->GetNDevices()-1);//-1是因为dev0一般是loopback
			sw->m_mmu->ConfigBufferSize(buffer_size* 1024 * 1024);//配置交换机总buffer大小，文件中的buffersize单位是MB
			sw->m_mmu->node_id = sw->GetId();
		}
	}

	#if ENABLE_QP
	FILE *fct_output = fopen(fct_output_file.c_str(), "w");
	//
	// install RDMA driver
	//
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 0){ // is server
			// create RdmaHw
			Ptr<RdmaHw> rdmaHw = CreateObject<RdmaHw>();//创建RDMA硬件对象，其可以维护QP,选择NIC，发送RDMA包，处理ACK/NACK/CNP，执行拥塞控制算法
			rdmaHw->SetAttribute("ClampTargetRate", BooleanValue(clamp_target_rate));
			rdmaHw->SetAttribute("AlphaResumInterval", DoubleValue(alpha_resume_interval));
			rdmaHw->SetAttribute("RPTimer", DoubleValue(rp_timer));
			rdmaHw->SetAttribute("FastRecoveryTimes", UintegerValue(fast_recovery_times));
			rdmaHw->SetAttribute("EwmaGain", DoubleValue(ewma_gain));
			rdmaHw->SetAttribute("RateAI", DataRateValue(DataRate(rate_ai)));
			rdmaHw->SetAttribute("RateHAI", DataRateValue(DataRate(rate_hai)));
			rdmaHw->SetAttribute("L2BackToZero", BooleanValue(l2_back_to_zero));
			rdmaHw->SetAttribute("L2ChunkSize", UintegerValue(l2_chunk_size));
			rdmaHw->SetAttribute("L2AckInterval", UintegerValue(l2_ack_interval));
			rdmaHw->SetAttribute("CcMode", UintegerValue(cc_mode));
			rdmaHw->SetAttribute("RateDecreaseInterval", DoubleValue(rate_decrease_interval));
			rdmaHw->SetAttribute("MinRate", DataRateValue(DataRate(min_rate)));
			rdmaHw->SetAttribute("Mtu", UintegerValue(packet_payload_size));
			rdmaHw->SetAttribute("MiThresh", UintegerValue(mi_thresh));
			rdmaHw->SetAttribute("VarWin", BooleanValue(var_win));
			rdmaHw->SetAttribute("FastReact", BooleanValue(fast_react));
			rdmaHw->SetAttribute("MultiRate", BooleanValue(multi_rate));
			rdmaHw->SetAttribute("SampleFeedback", BooleanValue(sample_feedback));
			rdmaHw->SetAttribute("TargetUtil", DoubleValue(u_target));
			rdmaHw->SetAttribute("RateBound", BooleanValue(rate_bound));
			rdmaHw->SetAttribute("DctcpRateAI", DataRateValue(DataRate(dctcp_rate_ai)));
			rdmaHw->SetPintSmplThresh(pint_prob);
			// create and install RdmaDriver
			Ptr<RdmaDriver> rdma = CreateObject<RdmaDriver>();//创建RDMA驱动对象
			Ptr<Node> node = n.Get(i);
			rdma->SetNode(node);
			rdma->SetRdmaHw(rdmaHw);

			node->AggregateObject (rdma);//node聚合RDMA
			rdma->Init();
			rdma->TraceConnectWithoutContext("QpComplete", MakeBoundCallback (qp_finish, fct_output));
		}
	}
	#endif

	// set ACK priority on hosts
	if (ack_high_prio)
		RdmaEgressQueue::ack_q_idx = 0;
	else
		RdmaEgressQueue::ack_q_idx = 3;

	// setup routing
	CalculateRoutes(n);
	SetRoutingEntries();

	//
	// get BDP and delay
	//
	maxRtt = maxBdp = 0;
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() != 0)//非host节点不行
			continue;
		for (uint32_t j = 0; j < node_num; j++){
			if (n.Get(j)->GetNodeType() != 0)
				continue;
			uint64_t delay = pairDelay[n.Get(i)][n.Get(j)];//获取两个host的传输delay
			uint64_t txDelay = pairTxDelay[n.Get(i)][n.Get(j)];//发送delay
			uint64_t rtt = delay * 2 + txDelay;//计算rtt
			uint64_t bw = pairBw[i][j];
			uint64_t bdp = rtt * bw / 1000000000/8; 
			pairBdp[n.Get(i)][n.Get(j)] = bdp;
			pairRtt[i][j] = rtt;
			if (bdp > maxBdp)
				maxBdp = bdp;
			if (rtt > maxRtt)
				maxRtt = rtt;
		}
	}//获取所有host之间的RTT与带宽时延积
	printf("maxRtt=%lu maxBdp=%lu\n", maxRtt, maxBdp);

	//
	// setup switch CC，选择交换机的CC算法以及最大RTT
	//
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 1){ // switch
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
			sw->SetAttribute("CcMode", UintegerValue(cc_mode));
			sw->SetAttribute("MaxRtt", UintegerValue(maxRtt));
		}
	}
		// RdmaDriver::Init connects each host QbbNetDevice with RdmaHw and
		// registers callbacks for receive, send completion, next-packet fetch,
		// link-down handling, and QP completion logging.
	//
	// add trace
	//

	NodeContainer trace_nodes;
	for (uint32_t i = 0; i < trace_num; i++)//这个for主要是读取需要trace的节点，每次读一个节点编号nid
	{
		uint32_t nid;
		tracef >> nid;
		if (nid >= n.GetN()){
			continue;
		}
		trace_nodes = NodeContainer(trace_nodes, n.Get(nid));//将节点id加入到容器中
	}

	FILE *trace_output = fopen(trace_output_file.c_str(), "w");
	if (enable_trace)
		qbb.EnableTracing(trace_output, trace_nodes);//绑定trace回调，也就是将tracenode中的节点开始trace

	// dump link speed to trace file
	{
		SimSetting sim_setting;
		for (auto i: nbr2if){
			for (auto j : i.second){
				uint16_t node = i.first->GetId();
				uint8_t intf = j.second.idx;
				uint64_t bps = DynamicCast<QbbNetDevice>(i.first->GetDevice(j.second.idx))->GetDataRate().GetBitRate();
				sim_setting.port_speed[node][intf] = bps;
			}
		}
		sim_setting.win = maxBdp;
		sim_setting.Serialize(trace_output);
	}

	Ipv4GlobalRoutingHelper::PopulateRoutingTables();

	NS_LOG_INFO("Create Applications.");

	Time interPacketInterval = Seconds(0.0000005 / 2);

	// maintain port number for each host，即初始化每一队host的端口号
	for (uint32_t i = 0; i < node_num; i++){
		if (n.Get(i)->GetNodeType() == 0)
			for (uint32_t j = 0; j < node_num; j++){
				if (n.Get(j)->GetNodeType() == 0)
					portNumder[i][j] = 10000; // each host pair use port number from 10000
			}
	}

	flow_input.idx = 0;//读取flow并开始调度启动
	if (flow_num > 0){
		ReadFlowInput();
		Simulator::Schedule(Seconds(flow_input.start_time)-Simulator::Now(), ScheduleFlowInputs);
	}

	topof.close();
	tracef.close();

	// schedule link down，文件中还设置了链路断开事件，也就是说可以在这里将链路断开
	if (link_down_time > 0){
		Simulator::Schedule(Seconds(2) + MicroSeconds(link_down_time), &TakeDownLink, n, n.Get(link_down_A), n.Get(link_down_B));
	}

	// schedule buffer monitor
	FILE* qlen_output = fopen(qlen_mon_file.c_str(), "w");
	Simulator::Schedule(NanoSeconds(qlen_mon_start), &monitor_buffer, qlen_output, &n);

	//
	// Now, do the actual simulation.
	//启动仿真
	std::cout << "Running Simulation.\n";
	fflush(stdout);
	NS_LOG_INFO("Run Simulation.");
	Simulator::Stop(Seconds(simulator_stop_time));
	Simulator::Run();
	Simulator::Destroy();
	NS_LOG_INFO("Done.");
	fclose(trace_output);

	endt = clock();
	std::cout << (double)(endt - begint) / CLOCKS_PER_SEC << "\n";

}
