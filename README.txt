在cmd ftx的資料裡，跑
1. "venv\bin\activate.bat"
2. "python"

在python console裡，跑
1. "import client"
# 離開console "quit()"

基本指令：

- 加可用帳號 (default 是我AI01)
    [取名] = client.FtxClient([api_key], [api_secret],[Optional: subaccount_name])
    例如：
    cliff = client.FtxClient('1lzuMlvkbTyhgf0qzqc7c_wGrrJQrPB0TZDt018f','XAGNmVjiM6Zrdcv2FBhZzyUr5JS4HtJBTjw9LVKr', 'cliff')
    # 換之後把 "cliff" 代替任何 "client.Client"
        # 例如 "cliff.run_positive("BTC", -0.1, 5, 1)"

- 開倉/正向
    client.Client.run_positive([幣種], [價差容許值], [跑次數], [跑間隔])
    例如：
    client.Client.run_positive("BTC", -0.1, 5, 1) -> 只要>-0.1%就跑，跑五次，每次間隔1秒

- 關倉/反向
    client.Client.run_negative([幣種], [價差容許值], [跑次數], [跑間隔])
    例如：
    client.Client.run_negative("BTC", 0.1, 5, 1) -> 只要<0.1%就跑，跑五次，每次間隔1秒

- 正向價差(用正向算法的價差)
    client.Client.positive_future_dif([合約幣種],[現價幣種])
    例如：
    client.Client.positive_future_dif("BTC-PERP","BTC/USD")

- 反向價差(用反向算法的價差)
    client.Client.negative_future_dif([合約幣種],[現價幣種])
    例如：
    client.Client.negative_future_dif("BTC-PERP","BTC/USD")

- 20天利率圖
    client.Client.graph_funding_rates([幣種]) 
    例如：
    client.Client.graph_funding_rates("BTC")

- 20天利潤圖
    client.Client.graph_payments(["幣種"])
    例如：
    client.Client.graph_payments("BTC")

- 平均年利率
    client.Client.fund_overtime([幣種],[天]) #1-20天
    例如：
    client.Client.fund_overtime("BTC", 20)
