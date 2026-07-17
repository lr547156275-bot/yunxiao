#include "ns3/core-module.h"

using namespace ns3;

void Hello()
{
    std::cout << "Now = " << Simulator::Now().GetMicroSeconds()
              << "us, hello ns-3" << std::endl;
    Simulator::Schedule(Seconds(1), &Hello);
    std::cout << "Now = " << Simulator::Now().GetMicroSeconds()
             << "us, hello 4" << std::endl;
}

int main()
{
    Time::SetResolution(Time::US);
    for(int i = 0;i <= 1;i++)
    {
        Simulator::Schedule(Seconds(1), &Hello);
    }
    Simulator::Stop(Seconds(4));
    Simulator::Run();
    Simulator::Destroy();

    return 0;
}

"""
可以在函数里面加一个调度来达到仿真前进的目的
"""