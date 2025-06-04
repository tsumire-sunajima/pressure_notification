# pressure_notification

気圧低下を検知し、Discordに通知するPythonスクリプトです。

## 機能概要
- OpenWeatherMap APIを利用して気圧予報を取得
- 独自ルールで気圧低下を判定し、Discord Webhookで通知
- 通知のクールダウンや状態管理機能あり

## セットアップ手順
1. Python 3.x をインストール
2. 仮想環境の作成
   ```sh
   python -m venv venv
   ```
3. 仮想環境の有効化
   - Windows:
     ```sh
     .\venv\Scripts\activate
     ```
   - Mac/Linux:
     ```sh
     source venv/bin/activate
     ```
4. 必要パッケージのインストール
   ```sh
   pip install -r requirements.txt
   ```
5. `.env` ファイルを作成し、以下の内容を記入
   ```env
   OPENWEATHERMAP_API_KEY=あなたのAPIキー
   DISCORD_WEBHOOK_URL=あなたのWebhookURL
   LATITUDE=あなたの緯度
   LONGITUDE=あなたの経度
   ```

## 実行方法
```sh
python pressure_notification.py
```

## 注意事項
- `.env` ファイルやAPIキーは絶対に公開しないでください。
- デバッグ用に `api_response_debug.json` が毎回上書き保存されます。

---

*このREADMEはAIによって自動生成されました。* 