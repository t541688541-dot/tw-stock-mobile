# GitHub Pages 手機版發布

這個專案現在會在桌面版更新快照時，自動同步輸出 GitHub Pages 用的靜態頁面到 `docs/`。

目前會自動產生：

- `docs/index.html`
- `docs/mobile_snapshot_offline.html`
- `docs/404.html`
- `docs/.nojekyll`

## 你之後怎麼用

1. 在桌面版 `tw_stock_gui.py` 先更新一次資料
2. 確認 `docs/index.html` 已更新
3. 把整個 repo push 到 GitHub
4. 到 GitHub 專案頁面開啟 `Settings -> Pages`
5. 若使用 GitHub Actions，保持預設即可  
   這個 repo 已經附上 `.github/workflows/deploy-github-pages.yml`
6. 第一次部署完成後，固定網址通常會是：

```text
https://你的 GitHub 帳號.github.io/你的 repo 名稱/
```

## 重點

- 這個網址會固定
- 電腦關機後仍可開啟
- 顯示內容會是最後一次 push 上 GitHub 的快照
- 若你今天更新了推薦結果，但沒有 push，GitHub Pages 上看到的仍會是上一次版本
