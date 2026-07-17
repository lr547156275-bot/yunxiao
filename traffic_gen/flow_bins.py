import sys
import random
import math
import heapq
from optparse import OptionParser
from custom_rand import CustomRand

if __name__ == "__main__":
	parser = OptionParser()#命令行解析器
	parser.add_option("-c", "--cdf", dest = "cdf_file", help = "the file of the traffic size cdf", default = "uniform_distribution.txt")
	options,args = parser.parse_args()

	fileName = options.cdf_file#取出CDF文件
	file = open(fileName,"r")
	lines = file.readlines()
	# read the cdf, save in cdf as [[x_i, cdf_i] ...]
	cdf = []
	for line in lines:
		x,y = map(float, line.strip().split(' '))
		cdf.append([x,y])#流大小和百分比

	# create a custom random generator, which takes a cdf, and generate number according to the cdf
	customRand = CustomRand()
	if not customRand.setCdf(cdf):
		print "Error: Not valid cdf"
		sys.exit(0)

	x = int(customRand.getValueFromPercentile(100))#获取percent100的时候流的大小
	p = 100.#从100%开始
	bins = []#创建桶
	while x > 0:
	#只要当前流大小还大于0，就继续往下找分桶。
		if (len(bins) == 0 or x != bins[-1]):#如果桶为空或者当前流大小和上一个桶不冲突就加入
			bins.append(x)#把当前流大小计入到桶中
		if (p > 2):
			p1 = p-1
		elif p > 1:#百分比在1-2之间直接跳到1
			p1 = 1
		else:#百分比为1或更低
			break
		x1 = int(customRand.getValueFromPercentile(p1))#查询下一跳流p1对应的流大小
		if x1 < x/2 and x > 1000:#如果下一个流大小比当前流大小小了一半以上，并且当前流大于1000bytes，说明跨度太大。
			x1 = x / 2#不直接跳到p1的大小，而是先取当前大小的一半作为中间分桶
			p1 = customRand.getPercentileFromValue(x1)#提取这个的百分比
		if p1 < 0:#如果查询失败
			print "error"
			print p1, bins
			sys.exit(0)
		x = x1#更新当前流大小和百分比
		p = p1
	bins.sort()#排序
	for x in bins:#遍历
		print x, customRand.getPercentileFromValue(x)
#这个函数就是想告诉我们我们这个流生成出来的，哪些算大流哪些算中流/大流/超大流比如说：
#小流：0 ~ 10KB
#中流：10KB ~ 100KB
#大流：100KB ~ 1MB
#超大流：1MB 以上