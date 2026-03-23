整个流程是这样的，skill第一次被调用，应该先在.runtime/env下安装python 环境，然后向用户询问access token, 这些skill应该已经都
可以做到了，再次确认一下。

如果用户说要跑某个trading agent, 应该检查一下rule里面是否有这个trading agent (判断是否agent id存在)
如果没有，应该create new rule with that agent id, 

然后问用户跑哪个股票还是打开图像界面给这个agent assign pool, 
这往后就有两种交互方式，用户可以通过命令assign pool, 也可以要求打开图形界面（backtests的前度后端）来操作。

如果用户要求的这个agent已经在rule 里面，而且已经有assigned pool ，那么直接运行这个pool里的所有股票就行了。

另外给这个backtests写一个让用户非常容易看懂的readme,backtests/README.md, 用户有问题的时候引导用户如何使用，没有问题的时候也可以给出简单
提示

总之这个skill现在是两个功能，一个是agent 远程运行和skill远程下载功能，
第二个就是trading agent的回测系统。


用户即可以通过UI界面操作回测系统，也可以通过命令行来操作回测系统。所以你backtests/README.md是给人看的，再写一份更详细的操作指南给LLM看，
让命令操作不会出问题，并且该加的限制也要加上，比如数据库里哪些可以改，比如增加pool， 给pool增加stocks哪些不能改，比如那些需要运行simulator才能产生的结果
写一份非常严格的操作手册给机器
