# GitHub Pages 第一次發布

目前專案已經準備好 GitHub Pages 所需內容：

- `docs/index.html`
- `docs/mobile_snapshot_offline.html`
- `.github/workflows/deploy-github-pages.yml`

## 一鍵腳本

已附上：

- `publish_github_pages.ps1`

用法：

```powershell
powershell -ExecutionPolicy Bypass -File .\publish_github_pages.ps1 -RepoUrl "https://github.com/你的帳號/你的repo.git"
```

## 第一次發布還需要的外部條件

1. 這台電腦要先安裝 Git for Windows
2. 你要先在 GitHub 建好空白 repo
3. 本機要能登入 GitHub 進行 push

## 發布後固定網址

```text
https://你的GitHub帳號.github.io/你的repo名稱/
```

## 之後更新

每次桌面版 GUI 更新完快照後：

1. `docs/index.html` 會自動更新
2. 再跑一次 push
3. GitHub Pages 就會更新成最新內容
