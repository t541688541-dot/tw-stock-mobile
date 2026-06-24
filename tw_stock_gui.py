import json
import os
import threading
import csv
import re
import subprocess
import sys
import time
import tkinter as tk
import webbrowser
from datetime import date, datetime
from html import escape
from tkinter import messagebox, simpledialog, ttk

import requests

from daily_tech_analysis import generate_daily_tech_dashboard
from screener_core import (
    BASE_DIR,
    TOP_RECOMMENDATIONS_CSV_PATH,
    USER_AGENT,
    StockCandidate,
    build_avg_revenue_growth_map,
    build_official_financial_map,
    build_preferred_dashboard,
    build_twse_history_map,
    build_twse_valuation_map,
    build_universe,
    default_config,
    fetch_market_index,
    fetch_realtime_quotes,
    fetch_stock_metrics_with_retry,
    save_csv,
)


PAGE_BG = "#f4f1ea"
PANEL_BG = "#ffffff"
CARD_BG = "#fcfbf7"
ACCENT_BG = "#dbe6ef"
HEADER_BG = "#eef4f1"
CHIP_BG = "#e8f3ec"
TEXT_DARK = "#1f2933"
TEXT_MID = "#5f6b76"
BORDER = "#ddd6c8"
UP_COLOR = "#c0392b"
DOWN_COLOR = "#1f8a5c"
FLAT_COLOR = "#6b7280"
SELECTED_COLOR = "#1f8a5c"
FALLBACK_COLOR = "#b7791f"
RANK_COLOR = "#3b4b5b"
LINK_COLOR = "#1d4ed8"
SELL_URGENT_COLOR = "#c0392b"
SELL_WATCH_COLOR = "#d97706"
SELL_OK_COLOR = "#1f8a5c"
WATCHLIST_PATH = BASE_DIR / "watchlist.json"
GUI_SNAPSHOT_PATH = BASE_DIR / "tw_stock_gui_snapshot.json"
PODCAST_OUTPUT_DIR = BASE_DIR / "podcast_output"
PODCAST_SIGNAL_PATH = PODCAST_OUTPUT_DIR / "podcast_signals.json"
MOBILE_OFFLINE_SNAPSHOT_PATH = BASE_DIR / "mobile_snapshot_offline.html"
MOBILE_OFFLINE_PUBLIC_PATH = BASE_DIR / "static" / "mobile_snapshot_offline.html"
MOBILE_SNAPSHOT_ARCHIVE_DIR = BASE_DIR / "mobile_snapshot_archive"
GITHUB_PAGES_DIR = BASE_DIR / "docs"
GITHUB_PAGES_INDEX_PATH = GITHUB_PAGES_DIR / "index.html"
GITHUB_PAGES_404_PATH = GITHUB_PAGES_DIR / "404.html"
GITHUB_PAGES_LATEST_PATH = GITHUB_PAGES_DIR / "mobile_snapshot_offline.html"
GITHUB_PAGES_NOJEKYLL_PATH = GITHUB_PAGES_DIR / ".nojekyll"
PODCAST_PROJECT_DIR = BASE_DIR / "podcast_llm_project"
PODCAST_ENV_PATH = PODCAST_PROJECT_DIR / ".env"
DAILY_ANALYSIS_REFRESH_SECONDS = 2 * 60 * 60
RANK_BADGES = ["🏆 冠軍", "🥈 亞軍", "🥉 季軍"]
RANK_CARD_STYLES = [
    ("#fff7df", "#d4af37"),
    ("#f3f4f6", "#9ca3af"),
    ("#fff1e7", "#c47a31"),
]


BUSINESS_SUMMARIES = {
    "2451": "創見為台灣知名記憶體與儲存設備品牌，產品涵蓋 DRAM 模組、SSD 固態硬碟、記憶卡、USB 隨身碟及工業級儲存方案。公司以自有品牌經營全球市場，擁有完整研發、製造與品管能力。強項在於品牌知名度高、產品線完整，並積極布局工控、車載及嵌入式儲存市場，提升產品附加價值與獲利穩定性。",
    "4967": "十銓專注於記憶體模組、SSD、記憶卡及電競儲存產品開發與銷售，旗下 TEAMGROUP、T-FORCE 等品牌在電競市場具一定知名度。公司以消費性與電競市場為核心，同時擴展工業級儲存產品。強項在於產品設計能力佳、品牌經營靈活，能快速掌握高效能運算與電競硬體需求成長趨勢。",
    "8271": "宇瞻主要從事記憶體模組、SSD 及工業級儲存設備研發與製造，兼具品牌與工控市場布局。公司長期深耕工業電腦、智慧製造、車載及邊緣運算應用，提供客製化儲存解決方案。強項在於工業級產品認證與技術門檻較高，客戶黏著度強，較不易受到消費性市場價格波動影響。",
    "6691": "洋基工程為高科技廠房機電與無塵室工程領導廠商，主要服務半導體、面板、生技及資料中心客戶。公司提供從設計、採購到施工的一站式統包服務，參與多項大型晶圓廠與先進封裝廠建設。強項在於具備高階無塵室工程經驗與技術門檻，能受惠於半導體資本支出與先進製程擴產需求。",
    "8112": "至上電子為半導體與電子零組件通路商，代理產品涵蓋記憶體、MCU、邏輯 IC 及各類電子元件，客戶遍及消費電子、工業控制及通訊設備領域。公司與國際晶片原廠維持長期合作關係，具備供應鏈整合與技術支援能力。強項在於通路規模大、客戶基礎廣，並能受惠於半導體景氣回升帶來的拉貨需求。",
    "2330": "台積電為全球晶圓代工龍頭，專注先進製程、成熟製程及先進封裝服務，客戶涵蓋手機、AI、高效能運算、車用與網通晶片設計大廠。公司核心競爭力在於製程技術領先、良率控制與龐大資本支出形成的規模門檻。強項是能持續受惠於 AI 晶片、高速運算與先進封裝需求成長。",
    "5434": "崇越科技為半導體材料、設備與電子零組件通路商，也跨足環工與高科技廠務相關服務。公司長期深耕半導體供應鏈，代理矽晶圓材料、化學品與多項關鍵設備，客戶基礎穩固。強項在於與上游原廠合作關係深、供應鏈整合能力強，能受惠於晶圓廠擴產與材料需求增加。",
    "2059": "川湖科技主要產品為伺服器導軌、機櫃滑軌及高階機構件，客戶涵蓋雲端資料中心與伺服器品牌廠。公司近年受惠於 AI 伺服器、高密度機櫃與資料中心建置需求快速升溫。強項在於高階導軌設計能力、產品單價與毛利率較佳，具備明顯的利基零組件優勢。",
    "2344": "華邦電為記憶體與邏輯 IC 業者，產品以 NOR Flash、NAND Flash、DRAM 及客製化記憶體解決方案為主，應用遍及消費電子、工控、車用與通訊。公司具備自有晶圓廠與產品開發能力，在利基型記憶體市場具有一定地位。強項在於產品線完整，並受惠於邊緣裝置與車用電子對非揮發性記憶體需求提升。",
    "3028": "增你強為半導體與電子零組件通路商，代理產品涵蓋記憶體、類比 IC、電源管理與各式關鍵元件，服務消費電子、工控與通訊客戶。公司以代理通路與技術支援為核心，重視客戶關係與供應鏈管理。強項在於通路覆蓋面廣、產品組合彈性高，可受惠於電子景氣回溫帶來的補庫存需求。",
    "6257": "矽格為國內重要半導體封裝測試服務廠，業務涵蓋晶圓測試、成品測試、封裝及可靠度驗證，客戶涵蓋 IC 設計與晶片供應鏈廠商。公司長期深耕記憶體、通訊與高速運算相關測試需求。強項在於測試產能與客戶黏著度高，能受惠於晶片出貨回升與高階測試需求增加。",
    "8016": "矽創電子為顯示器驅動 IC 與觸控相關晶片設計公司，產品應用於手機、筆電、顯示器、車載與工控面板。公司在中小尺寸與利基型顯示驅動領域具備技術實力，並積極切入車載顯示與高附加價值應用。強項在於產品客製化能力與利基市場布局，毛利結構相對較佳。",
    "3711": "日月光投控為全球封裝測試龍頭之一，集團業務涵蓋封裝、測試、電子代工與系統整合服務，客戶遍及國際半導體大廠。公司在先進封裝、系統級封裝與高階測試具規模優勢。強項在於產能完整、技術平台齊全，能受惠於 AI、高速運算與異質整合帶來的先進封裝需求。",
    "8131": "福懋科為半導體封裝與測試廠，主要產品與服務聚焦記憶體及相關 IC 封測需求，客戶多為記憶體與晶片供應鏈業者。公司長期深耕後段製程，營運與記憶體景氣循環關聯度高。強項在於既有客戶基礎與封測經驗，可在記憶體市場回溫時受惠出貨增加。",
    "6672": "騰輝電子主要從事銅箔基板與特殊材料開發，產品應用於伺服器、高速傳輸、車用電子及高階 PCB 領域。公司在高頻高速材料、散熱與利基板材市場積極布局。強項在於材料技術門檻較高，能受惠於 AI 伺服器、高速通訊與高階電路板升級趨勢。",
    "2308": "台達電為電源管理與散熱解決方案大廠，產品涵蓋電源供應器、工業自動化、資料中心基礎設施、電動車零組件與樓宇能源管理。公司近年積極布局高功率電源、液冷散熱與能源基礎建設。強項在於電源效率技術、全球客戶基礎與跨領域整合能力，受惠於 AI 伺服器與節能趨勢。",
    "2480": "敦陽科技為資訊服務與系統整合廠商，業務涵蓋企業資訊基礎架構、雲端、資安、資料庫與維運服務。公司主要客戶來自政府、金融、電信與大型企業，收入結構偏向專案與維護並重。強項在於企業級專案經驗深、技術團隊完整，能持續受惠於數位轉型與資安投資需求。",
    "6214": "精誠資訊為台灣大型資訊服務與軟體整合業者，提供雲端、數據、資安、金融科技與企業數位轉型解決方案。公司服務範圍涵蓋企業、金融與公部門客戶，並透過多子公司經營不同垂直應用。強項在於客戶基礎廣、解決方案完整，可受惠於企業 IT 支出與 AI 應用導入。",
    "8046": "南電為 ABF 載板與高階印刷電路板大廠，產品應用於 CPU、GPU、網通晶片與高速運算平台，是先進半導體封裝的重要供應鏈成員。公司在高階載板領域具備製程與客戶認證門檻。強項在於受惠於 AI 晶片、高速運算與先進封裝擴產，載板需求具中長期成長性。",
    "6770": "力積電為晶圓代工與記憶體製造相關業者，聚焦成熟製程、特殊製程與顯示驅動、電源管理等晶片代工需求，也具備記憶體製造背景。公司在成熟製程與特定應用市場具一定客戶基礎。強項在於可承接多元利基晶片需求，並受惠於景氣回升時的產能利用率改善。",
    "2404": "主要業務為高科技廠房工程、無塵室與機電系統整合，核心客戶多集中在半導體與高階製造業。強項在整體建廠能力、跨系統協調與大型專案執行，受惠於晶圓廠與先進封裝擴產需求。",
    "3025": "主要業務為網通與無線通訊設備，產品涵蓋企業級通訊、無線傳輸與專網應用。強項在通訊技術整合、客製化能力與企業客戶導入經驗，成長動能常來自企業升級與特定應用擴建。",
    "5434": "主要業務為半導體與光電材料供應，橫跨材料通路、技術服務與製程支援。強項在高科技供應鏈整合、客戶黏著度與利基材料經營，通常受惠於半導體與光電景氣回升。",
    "6139": "主要業務為無塵室、機電與高科技工程統包，服務範圍涵蓋廠務系統、機電整合與大型工程建置。強項在整體系統整合、海外大型專案執行與高規格客戶驗證，常被視為高科技建廠循環的重要受惠股。",
    "6197": "主要業務為連接器與高速傳輸線材，產品應用在伺服器、AI、高速運算與工業設備。強項在高速訊號傳輸設計、客製化規格與高階客戶供應鏈地位，受惠於資料中心升級與 AI 基礎建設擴張。",
    "2357": "主要業務為品牌電腦、伺服器、主機板與電競產品，橫跨消費性與企業級運算市場。強項在產品設計、品牌經營與高階平台整合，若伺服器與 AI 相關產品放量，通常能帶動獲利結構改善。",
    "2472": "主要業務為鋁質電解電容，產品廣泛應用於工控、電源模組、車用與通訊設備。強項在製造良率、長期客戶關係與多元終端應用，景氣回升時具備業績彈性。",
    "3312": "主要業務為記憶體與電子零組件通路，扮演供應鏈分銷與客戶配貨的重要角色。強項在供應鏈整合、庫存調度與快速反應能力，若記憶體景氣與零組件需求改善，營運表現通常跟著受惠。",
    "2467": "主要業務為自動化設備與 PCB/半導體製程設備，客戶多來自電子製造與高階製程領域。強項在精密製造、設備整合與產線升級需求，常受惠於電子製造業資本支出循環。",
    "2368": "主要業務為 PCB 與高速板材製造，產品應用於伺服器、網通、高速運算與高階電子設備。強項在高層數板、伺服器板與高規格製程能力，產業趨勢若往高頻高速走，受惠程度通常較高。",
}

BUSINESS_SUMMARIES.update(
    {
        "2451": "創見為台灣知名記憶體與儲存設備品牌，產品涵蓋 DRAM 模組、SSD 固態硬碟、記憶卡、USB 隨身碟及工業級儲存方案。公司以自有品牌經營全球市場，擁有完整研發、製造與品管能力。強項在於品牌知名度高、產品線完整，並積極布局工控、車載及嵌入式儲存市場，提升產品附加價值與獲利穩定性。",
        "4967": "十銓專注於記憶體模組、SSD、記憶卡及電競儲存產品開發與銷售，旗下 TEAMGROUP、T-FORCE 等品牌在電競市場具一定知名度。公司以消費性與電競市場為核心，同時擴展工業級儲存產品。強項在於產品設計能力佳、品牌經營靈活，能快速掌握高效能運算與電競硬體需求成長趨勢。",
        "8271": "宇瞻主要從事記憶體模組、SSD 及工業級儲存設備研發與製造，兼具品牌與工控市場布局。公司長期深耕工業電腦、智慧製造、車載及邊緣運算應用，提供客製化儲存解決方案。強項在於工業級產品認證與技術門檻較高，客戶黏著度強，較不易受到消費性市場價格波動影響。",
        "6691": "洋基工程為高科技廠房機電與無塵室工程領導廠商，主要服務半導體、面板、生技及資料中心客戶。公司提供從設計、採購到施工的一站式統包服務，參與多項大型晶圓廠與先進封裝廠建設。強項在於具備高階無塵室工程經驗與技術門檻，能受惠於半導體資本支出與先進製程擴產需求。",
        "8112": "至上電子為半導體與電子零組件通路商，代理產品涵蓋記憶體、MCU、邏輯 IC 及各類電子元件，客戶遍及消費電子、工業控制及通訊設備領域。公司與國際晶片原廠維持長期合作關係，具備供應鏈整合與技術支援能力。強項在於通路規模大、客戶基礎廣，並能受惠於半導體景氣回升帶來的拉貨需求。",
        "2330": "台積電為全球晶圓代工龍頭，專注先進製程、成熟製程及先進封裝服務，客戶涵蓋手機、AI、高效能運算、車用與網通晶片設計大廠。公司核心競爭力在於製程技術領先、良率控制與龐大資本支出形成的規模門檻。強項是能持續受惠於 AI 晶片、高速運算與先進封裝需求成長。",
        "5434": "崇越科技為半導體材料、設備與電子零組件通路商，也跨足環工與高科技廠務相關服務。公司長期深耕半導體供應鏈，代理矽晶圓材料、化學品與多項關鍵設備，客戶基礎穩固。強項在於與上游原廠合作關係深、供應鏈整合能力強，能受惠於晶圓廠擴產與材料需求增加。",
        "2059": "川湖科技主要產品為伺服器導軌、機櫃滑軌及高階機構件，客戶涵蓋雲端資料中心與伺服器品牌廠。公司近年受惠於 AI 伺服器、高密度機櫃與資料中心建置需求快速升溫。強項在於高階導軌設計能力、產品單價與毛利率較佳，具備明顯的利基零組件優勢。",
        "2344": "華邦電為記憶體與邏輯 IC 業者，產品以 NOR Flash、NAND Flash、DRAM 及客製化記憶體解決方案為主，應用遍及消費電子、工控、車用與通訊。公司具備自有晶圓廠與產品開發能力，在利基型記憶體市場具有一定地位。強項在於產品線完整，並受惠於邊緣裝置與車用電子對非揮發性記憶體需求提升。",
        "3028": "增你強為半導體與電子零組件通路商，代理產品涵蓋記憶體、類比 IC、電源管理與各式關鍵元件，服務消費電子、工控與通訊客戶。公司以代理通路與技術支援為核心，重視客戶關係與供應鏈管理。強項在於通路覆蓋面廣、產品組合彈性高，可受惠於電子景氣回溫帶來的補庫存需求。",
        "6257": "矽格為國內重要半導體封裝測試服務廠，業務涵蓋晶圓測試、成品測試、封裝及可靠度驗證，客戶涵蓋 IC 設計與晶片供應鏈廠商。公司長期深耕記憶體、通訊與高速運算相關測試需求。強項在於測試產能與客戶黏著度高，能受惠於晶片出貨回升與高階測試需求增加。",
        "8016": "矽創電子為顯示器驅動 IC 與觸控相關晶片設計公司，產品應用於手機、筆電、顯示器、車載與工控面板。公司在中小尺寸與利基型顯示驅動領域具備技術實力，並積極切入車載顯示與高附加價值應用。強項在於產品客製化能力與利基市場布局，毛利結構相對較佳。",
        "3711": "日月光投控為全球封裝測試龍頭之一，集團業務涵蓋封裝、測試、電子代工與系統整合服務，客戶遍及國際半導體大廠。公司在先進封裝、系統級封裝與高階測試具規模優勢。強項在於產能完整、技術平台齊全，能受惠於 AI、高速運算與異質整合帶來的先進封裝需求。",
        "8131": "福懋科為半導體封裝與測試廠，主要產品與服務聚焦記憶體及相關 IC 封測需求，客戶多為記憶體與晶片供應鏈業者。公司長期深耕後段製程，營運與記憶體景氣循環關聯度高。強項在於既有客戶基礎與封測經驗，可在記憶體市場回溫時受惠出貨增加。",
        "6672": "騰輝電子主要從事銅箔基板與特殊材料開發，產品應用於伺服器、高速傳輸、車用電子及高階 PCB 領域。公司在高頻高速材料、散熱與利基板材市場積極布局。強項在於材料技術門檻較高，能受惠於 AI 伺服器、高速通訊與高階電路板升級趨勢。",
        "2308": "台達電為電源管理與散熱解決方案大廠，產品涵蓋電源供應器、工業自動化、資料中心基礎設施、電動車零組件與樓宇能源管理。公司近年積極布局高功率電源、液冷散熱與能源基礎建設。強項在於電源效率技術、全球客戶基礎與跨領域整合能力，受惠於 AI 伺服器與節能趨勢。",
        "2480": "敦陽科技為資訊服務與系統整合廠商，業務涵蓋企業資訊基礎架構、雲端、資安、資料庫與維運服務。公司主要客戶來自政府、金融、電信與大型企業，收入結構偏向專案與維護並重。強項在於企業級專案經驗深、技術團隊完整，能持續受惠於數位轉型與資安投資需求。",
        "6214": "精誠資訊為台灣大型資訊服務與軟體整合業者，提供雲端、數據、資安、金融科技與企業數位轉型解決方案。公司服務範圍涵蓋企業、金融與公部門客戶，並透過多子公司經營不同垂直應用。強項在於客戶基礎廣、解決方案完整，可受惠於企業 IT 支出與 AI 應用導入。",
        "8046": "南電為 ABF 載板與高階印刷電路板大廠，產品應用於 CPU、GPU、網通晶片與高速運算平台，是先進半導體封裝的重要供應鏈成員。公司在高階載板領域具備製程與客戶認證門檻。強項在於受惠於 AI 晶片、高速運算與先進封裝擴產，載板需求具中長期成長性。",
        "6770": "力積電為晶圓代工與記憶體製造相關業者，聚焦成熟製程、特殊製程與顯示驅動、電源管理等晶片代工需求，也具備記憶體製造背景。公司在成熟製程與特定應用市場具一定客戶基礎。強項在於可承接多元利基晶片需求，並受惠於景氣回升時的產能利用率改善。",
    }
)

INDUSTRY_SUMMARIES = {
    "半導體業": "主要業務圍繞晶片設計、製造或半導體供應鏈服務，常見成長動能來自先進製程、AI 晶片與高效能運算需求。這類公司強項通常在技術門檻、產能利用率與產業景氣回升時的獲利彈性。",
    "電腦及週邊設備業": "主要業務為伺服器、電腦、儲存或相關週邊設備，受惠主因多來自企業 IT 升級、資料中心擴建與 AI 伺服器需求。強項通常在系統整合、規格升級與品牌或代工客戶基礎。",
    "通信網路業": "主要業務為網通設備、傳輸模組與企業通訊系統，產業成長常與頻寬升級、資料中心互聯與企業網路建置有關。強項通常在高速傳輸能力、企業級導入經驗與通訊技術整合。",
    "電子零組件業": "主要業務為關鍵零組件供應，涵蓋連接器、板材、被動元件或傳輸模組等領域。強項在規格升級、客製化能力與長期供應鏈合作，若高階應用需求擴大，獲利通常有放大空間。",
    "資訊服務業": "主要業務為軟體、資訊整合、雲端或企業服務，通常受惠於企業數位化、自動化與資訊安全升級。強項在專案導入、維運服務與長期客戶黏著度。",
    "其他電子業": "主要業務偏向利基電子應用、系統設備或專業製造服務，營運表現常取決於客戶專案進度與產業投資節奏。強項在客製化能力、專業驗證門檻與跨系統整合。",
    "電機機械": "主要業務為自動化設備、工業應用或製程機台，常受惠於工廠升級、自動化投資與設備汰換循環。強項在精密製造、設備整合與提升客戶生產效率。",
}


def trend_text(row):
    pct = row.get("price_change_pct")
    if pct is None:
        return "--", FLAT_COLOR
    if pct > 0:
        return f"▲ {pct:.2f}%", UP_COLOR
    if pct < 0:
        return f"▼ {abs(pct):.2f}%", DOWN_COLOR
    return "0.00%", FLAT_COLOR


def strategy_lines():
    return [
        "EPS > 2 且 EPS 年增 > 10%",
        "(近 3 個月 YoY > 10%).sum() >= 2",
        "今日收盤價 > 前 60 日最高價 × 1.01",
        "成交量 > 20 日均量",
        "近 20 日漲幅 < 25%",
        "排除紡織、橡膠、百貨、觀光",
        "ROE > 20%",
        "股價 / 60MA > 1.05 且 ATR / 股價 < 8%",
    ]


def build_condition_rows(row):
    hard_flags = row.get("hard_filter_flags", {})
    bonus_flags = row.get("bonus_flags", {})
    return [
        ("EPS > 2 且 EPS 年增 > 10%", hard_flags.get("eps_and_eps_growth")),
        ("ROE > 20%", hard_flags.get("roe")),
        ("近 3 個月營收動能 > 10%", hard_flags.get("revenue")),
        ("近 20 日漲幅 < 25%", hard_flags.get("pullback_cap")),
        ("突破 60 日高點 1%", bonus_flags.get("breakout_60d")),
        ("成交量 > 20 日均量", bonus_flags.get("volume_above_avg20")),
        ("技術強度通過", bonus_flags.get("technical_strength")),
    ]


def fallback_business_summary(row):
    industry_name = row.get("industry_name") or row.get("industry") or ""
    broad_industry = row.get("broad_industry_name") or ""
    summary = BUSINESS_SUMMARIES.get(row.get("code"))
    if not summary:
        summary = INDUSTRY_SUMMARIES.get(industry_name) or INDUSTRY_SUMMARIES.get(broad_industry)
    if not summary:
        bits = []
        if industry_name:
            bits.append(f"主要業務屬於{industry_name}")
        if broad_industry and broad_industry != industry_name:
            bits.append(f"產業定位偏向{broad_industry}")
        if row.get("avg_revenue_growth_3m") is not None:
            bits.append(f"近 3 月平均年增 {row['avg_revenue_growth_3m']:.2f}%")
        if row.get("roe") is not None:
            bits.append(f"ROE {row['roe']:.2f}%")
        summary = "，".join(bits) if bits else "主要業務與產業定位資訊尚未補齊，建議搭配公司公告與法說資料判讀。"
    return {"summary": summary, "label": "", "url": ""}


def build_sell_reasons(row):
    urgent = []
    watch = []
    rsi = row.get("rsi")
    if rsi is not None and rsi > 80:
        watch.append(f"技術面：RSI {rsi:.2f} 已超過 80，股價有過熱風險。")

    macd_hist = row.get("macd_histogram")
    prev_macd_hist = row.get("prev_macd_histogram")
    if prev_macd_hist is not None and macd_hist is not None and prev_macd_hist > 0 >= macd_hist:
        urgent.append("技術面：MACD 柱狀體由正轉負，屬於死叉訊號。")

    price = row.get("price")
    ma20 = row.get("ma20")
    if price is not None and ma20 is not None and price < ma20:
        urgent.append(f"技術面：股價 {price:.2f} 已跌破 MA20 {ma20:.2f}。")

    atr_ratio = row.get("atr_ratio")
    if atr_ratio is not None and atr_ratio > 8:
        urgent.append(f"技術面：ATR / 股價為 {atr_ratio:.2f}%，波動已高於 8%。")

    growths = [value for value in (row.get("monthly_revenue_growths_3m") or []) if value is not None]
    if len(growths) >= 2:
        last_two = growths[-2:]
        if all(value < 0 for value in last_two):
            urgent.append(f"基本面：最近 2 個月營收 YoY 皆為負成長，分別為 {last_two[0]:.2f}% 與 {last_two[1]:.2f}%。")
        elif all(value < 10 for value in last_two):
            watch.append(f"基本面：最近 2 個月營收 YoY 都低於 10%，分別為 {last_two[0]:.2f}% 與 {last_two[1]:.2f}%。")

    eps_growth = row.get("eps_growth")
    if eps_growth is not None and eps_growth < 0:
        urgent.append(f"基本面：EPS 年增率已轉負，目前為 {eps_growth:.2f}%。")

    roe = row.get("roe")
    roe_prev = row.get("roe_prev_quarter")
    if roe_prev is not None and roe is not None and roe_prev >= 15 and roe < 8:
        urgent.append(f"基本面：ROE 從前一季 {roe_prev:.2f}% 明顯下滑到 {roe:.2f}%。")

    if urgent:
        return "立即留意", urgent + watch
    if watch:
        return "偏弱觀察", watch
    return "暫無訊號", []


def load_watchlist_data():
    if not WATCHLIST_PATH.exists():
        return {"stocks": [], "history": {}}
    try:
        with WATCHLIST_PATH.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return {"stocks": [], "history": {}}
    stocks = payload.get("stocks") or []
    history = payload.get("history") or {}
    return {"stocks": stocks, "history": history}


def save_watchlist_data(payload):
    with WATCHLIST_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def load_json_payload(path):
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
    except Exception:
        return {}
    return {}


def load_podcast_recommendations():
    csv_path = PODCAST_OUTPUT_DIR / "podcast_recommendations.csv"
    if not csv_path.exists():
        return []
    rows = []
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(row)
    except Exception:
        return []
    return rows


def load_podcast_signal_payload():
    payload = load_json_payload(PODCAST_SIGNAL_PATH)
    return payload if isinstance(payload, dict) else {}


def format_podcast_signal_source(signal_source: str, generation_mode: str = "") -> str:
    normalized_mode = str(generation_mode).strip().lower()
    if normalized_mode == "podcast_transcript_llm":
        return "LLM 逐字稿生成"
    if normalized_mode == "full_llm_generation":
        return "LLM 生成式選股"
    return "LLM" if str(signal_source).strip().lower() == "llm" else "fallback 規則"


def load_podcast_report_meta():
    md_path = PODCAST_OUTPUT_DIR / "podcast_recommendations.md"
    signal_payload = load_podcast_signal_payload()
    result = {
        "episode_id": str(signal_payload.get("episode_id") or "--"),
        "episode": str(signal_payload.get("title") or "--"),
        "published": str(signal_payload.get("date") or "--"),
        "signal_source": str(signal_payload.get("signal_source") or "rule"),
        "generation_mode": str(signal_payload.get("generation_mode") or ""),
        "summary": str(signal_payload.get("summary") or ""),
        "main_themes": signal_payload.get("main_themes") or [],
        "industries": signal_payload.get("industries") or [],
        "stock_candidates": signal_payload.get("stock_candidates") or [],
    }
    if not md_path.exists():
        return result
    try:
        lines = md_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return result
    summary_lines = []
    in_summary = False
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("- Episode:"):
            result["episode"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Episode ID:"):
            result["episode_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Published:") or line.startswith("- Date:"):
            result["published"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Signals:") and not signal_payload:
            signal_text = line.split(":", 1)[1].strip().lower()
            result["signal_source"] = "llm" if "llm" in signal_text else "rule"
        elif line.startswith("## 本集重點摘要") or line.startswith("## 本集主題"):
            in_summary = True
        elif line.startswith("## ") and in_summary:
            in_summary = False
        elif in_summary and line.startswith("- "):
            summary_lines.append(line[2:].strip())
    result["summary"] = "\n".join(summary_lines)
    return result


def fallback_candidate_from_code(code, name=None, market="") -> StockCandidate:
    clean_code = str(code).strip()
    clean_market = str(market or "").strip()
    if clean_market == "TWSE":
        symbol = f"{clean_code}.TW"
    elif clean_market == "TPEX":
        symbol = f"{clean_code}.TWO"
    else:
        symbol = clean_code
    return StockCandidate(clean_code, name or clean_code, clean_market, "Unknown", symbol)


def build_fallback_candidate_map():
    candidates = {}

    dashboard = load_json_payload(BASE_DIR / "preferred_dashboard_cache.json")
    for key in ("top_stocks", "passed_stocks", "fallback_stocks"):
        for row in dashboard.get(key, []) or []:
            code = str(row.get("code") or "").strip()
            if code and code.isdigit():
                candidates[code] = fallback_candidate_from_code(code, row.get("name"), row.get("market"))

    watchlist = load_watchlist_data()
    for item in watchlist.get("stocks", []) or []:
        code = str(item.get("code") or "").strip()
        if code and code.isdigit():
            candidates.setdefault(code, fallback_candidate_from_code(code, item.get("name"), item.get("market")))

    history_snapshot = load_json_payload(BASE_DIR / "twse_history_snapshot.json")
    history_data = history_snapshot.get("data", {}) if isinstance(history_snapshot.get("data"), dict) else {}
    for code in history_data:
        clean_code = str(code).strip()
        if clean_code and clean_code.isdigit():
            candidates.setdefault(clean_code, fallback_candidate_from_code(clean_code))

    return candidates


def to_float(value):
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def today_close_date_text() -> str:
    return date.today().strftime("%Y%m%d")


def display_date(date_text: str) -> str:
    if len(str(date_text)) == 8:
        return f"{date_text[:4]}-{date_text[4:6]}-{date_text[6:]}"
    return str(date_text or "--")


def latest_history_date(history_map) -> str:
    latest = ""
    for rows in (history_map or {}).values():
        if rows:
            row_date = str(rows[-1].get("date") or "")
            if row_date > latest:
                latest = row_date
    return latest


def format_close_status(latest_date: str) -> str:
    if latest_date:
        return f"收盤價：已讀取 {display_date(latest_date)}"
    return "收盤價：尚未讀到官方收盤資料"


def build_gui_snapshot_payload(
    dashboard=None,
    watch_rows=None,
    latest_close_date="",
    quote_updated=0,
    quote_failed=0,
    market_index=None,
    quote_date="",
    analysis_payload=None,
    podcast_meta=None,
    podcast_rows=None,
):
    return {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dashboard": dashboard or {},
        "watch_rows": watch_rows or [],
        "latest_close_date": latest_close_date or "",
        "quote_updated": int(quote_updated or 0),
        "quote_failed": int(quote_failed or 0),
        "market_index": market_index or {},
        "quote_date": quote_date or "",
        "analysis": analysis_payload or {},
        "podcast": {
            "meta": podcast_meta or {},
            "rows": podcast_rows or [],
        },
    }


def build_watch_rows_from_history_payload(watchlist_data):
    result = []
    history = watchlist_data.get("history", {}) if isinstance(watchlist_data, dict) else {}
    for item in (watchlist_data.get("stocks", []) if isinstance(watchlist_data, dict) else []):
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        code_history = history.get(code, {})
        latest_date = max(code_history) if code_history else ""
        latest = code_history.get(latest_date, {}) if latest_date else {}
        result.append(
            {
                "code": code,
                "name": item.get("name", code),
                "price": to_float(latest.get("price")),
                "previous_close": to_float(latest.get("previous_close")),
                "price_change_pct": to_float(latest.get("change_pct")),
                "realtime_at": latest_date,
            }
        )
    return result


def podcast_signal_sections(meta):
    candidate_labels = []
    for item in meta.get("stock_candidates") or []:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").strip()
        company = str(item.get("company") or "").strip()
        confidence = item.get("confidence_score")
        base = " ".join(part for part in [ticker, company] if part)
        if confidence not in (None, ""):
            candidate_labels.append(f"{base} (信心 {confidence})".strip())
        else:
            candidate_labels.append(base)
    return {
        "source": format_podcast_signal_source(meta.get("signal_source", "rule"), meta.get("generation_mode", "")),
        "main_themes": [str(item).strip() for item in (meta.get("main_themes") or []) if str(item).strip()],
        "industries": [str(item).strip() for item in (meta.get("industries") or []) if str(item).strip()],
        "stock_candidates": candidate_labels,
    }


def build_watchlist_snapshot_cards(watchlist_data, watch_rows):
    row_map = {str(item.get("code") or ""): item for item in (watch_rows or []) if item.get("code")}
    history = watchlist_data.get("history", {}) if isinstance(watchlist_data, dict) else {}
    cards = []
    for item in (watchlist_data.get("stocks", []) if isinstance(watchlist_data, dict) else []):
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        row = row_map.get(code)
        latest_date = "--"
        latest_price = "--"
        previous_close = "--"
        trend_value = "--"
        trend_class = "flat"
        sell_level = "資料不足"
        sell_message = "尚未同步賣出訊號，請先在桌面版更新一次自選股。"
        if row:
            level, reasons = build_sell_reasons(row)
            sell_level = level
            sell_message = "；".join(reasons) if reasons else f"{level}，目前沒有明確賣出訊號。"
            latest_date = str(row.get("realtime_at") or "--")
            latest_price = "--" if row.get("price") in (None, "") else f"{float(row['price']):.2f}"
            previous_close = "--" if row.get("previous_close") in (None, "") else f"{float(row['previous_close']):.2f}"
            trend_value, _trend_color = trend_text(row)
            trend_class = "up" if trend_value.startswith("▲") else "down" if trend_value.startswith("▼") else "flat"
        else:
            code_history = history.get(code, {})
            if code_history:
                latest_date = max(code_history)
                latest = code_history.get(latest_date, {})
                latest_price = "--" if latest.get("price") in (None, "") else f"{float(latest['price']):.2f}"
                previous_close = "--" if latest.get("previous_close") in (None, "") else f"{float(latest['previous_close']):.2f}"
                change_pct = latest.get("change_pct")
                if change_pct not in (None, ""):
                    change_value = float(change_pct)
                    trend_value = f"{change_value:+.2f}%"
                    trend_class = "up" if change_value > 0 else "down" if change_value < 0 else "flat"
        cards.append(
            {
                "code": code,
                "name": item.get("name", code),
                "price": latest_price,
                "previous_close": previous_close,
                "trend_value": trend_value,
                "trend_class": trend_class,
                "sell_level": sell_level,
                "sell_message": sell_message,
                "updated": latest_date,
            }
        )
    return cards


def render_mobile_offline_snapshot(snapshot_payload, watchlist_data, podcast_meta, podcast_rows, analysis_payload):
    dashboard = snapshot_payload.get("dashboard", {}) if isinstance(snapshot_payload, dict) else {}
    rows = (dashboard.get("top_stocks") or [])[:5]
    analysis = analysis_payload or {}
    topics = analysis.get("topics", [])[:3]
    companies = analysis.get("companies", [])[:5]
    news_items = analysis.get("news", [])[:5]
    watch_cards = build_watchlist_snapshot_cards(watchlist_data or {}, snapshot_payload.get("watch_rows") or [])
    podcast_sections = podcast_signal_sections(podcast_meta or {})
    generated_at = escape(str((snapshot_payload or {}).get("saved_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    snapshot_date = escape(str(dashboard.get("snapshot_date") or "--"))
    analyzed_count = int(dashboard.get("analyzed_count") or 0)
    failed_count = int(dashboard.get("failed_count") or 0)

    def chips(items):
        if not items:
            return '<span class="chip empty-chip">目前沒有資料</span>'
        return "".join(f'<span class="chip">{escape(str(item))}</span>' for item in items)

    def stock_cards():
        if not rows:
            return '<p class="empty">目前沒有可顯示的技術面推薦。</p>'
        parts = []
        for index, row in enumerate(rows, start=1):
            summary = fallback_business_summary(row).get("summary", "")
            change_pct = to_float(row.get("price_change_pct"))
            trend_class = "up" if change_pct and change_pct > 0 else "down" if change_pct and change_pct < 0 else "flat"
            trend_text_value = "--" if change_pct is None else f"{change_pct:+.2f}%"
            parts.append(
                f"""
                <article class="card">
                  <div class="row">
                    <div>
                      <div class="title">{index}. {escape(str(row.get('name') or row.get('code') or '--'))}</div>
                      <div class="subtle">{escape(str(row.get('code') or '--'))} / {escape(str(row.get('industry_name') or '--'))}</div>
                    </div>
                    <div class="price-block">
                      <div class="price">{'--' if row.get('price') in (None, '') else escape(f"{float(row['price']):.2f}")}</div>
                      <div class="{trend_class}">{escape(trend_text_value)}</div>
                    </div>
                  </div>
                  <div class="chips">
                    <span class="chip">總分 {escape(str(row.get('recommendation_score') or '--'))}</span>
                    <span class="chip">條件 {escape(str(row.get('total_match_count') or '--'))}</span>
                    <span class="chip">{escape(str(row.get('selection_tier') or '--'))}</span>
                  </div>
                  <p>{escape(summary)}</p>
                </article>
                """
            )
        return "".join(parts)

    def topic_cards():
        if not topics:
            return '<p class="empty">目前沒有新聞面話題快照。</p>'
        return "".join(
            f"""
            <article class="card">
              <div class="title">{escape(str(topic.get('name') or '--'))}</div>
              <div class="subtle">持續時間 {escape(str(topic.get('duration') or '--'))}</div>
              <p>驅動：{escape(str(topic.get('driver') or '--'))}</p>
              <p>瓶頸：{escape(str(topic.get('bottleneck') or '--'))}</p>
            </article>
            """
            for topic in topics
        )

    def news_cards():
        if not news_items:
            return '<p class="empty">目前沒有新聞摘要。</p>'
        return "".join(
            f"""
            <article class="card">
              <div class="title">{escape(str(item.get('summary') or item.get('title') or '--'))}</div>
              <div class="subtle">{escape(str(item.get('source') or '--'))} / {escape(str(item.get('published') or '--'))}</div>
              <p>影響：{escape(' / '.join(item.get('impacts') or []))}</p>
            </article>
            """
            for item in news_items
        )

    def company_cards():
        if not companies:
            return '<p class="empty">目前沒有新聞面受惠股。</p>'
        return "".join(
            f"""
            <article class="card">
              <div class="title">{escape(str(company.get('name') or '--'))} ({escape(str(company.get('code') or '--'))})</div>
              <div class="chips">
                <span class="chip">{escape(str(company.get('degree') or '--'))}</span>
                <span class="chip">{escape(str(company.get('topics') or '--'))}</span>
              </div>
            </article>
            """
            for company in companies
        )

    def podcast_cards():
        if not podcast_rows:
            return '<p class="empty">目前沒有股癌推薦結果。</p>'
        parts = []
        for index, row in enumerate(podcast_rows[:10], start=1):
            parts.append(
                f"""
                <article class="card">
                  <div class="row">
                    <div>
                      <div class="title">{index}. {escape(str(row.get('company') or row.get('ticker') or '--'))}</div>
                      <div class="subtle">{escape(str(row.get('ticker') or '--'))} / {escape(str(row.get('industry') or '--'))}</div>
                    </div>
                    <div class="price-block">
                      <div class="price">{escape(str(row.get('price') or '--'))}</div>
                      <div class="subtle">信心 {escape(str(row.get('confidence_score') or '--'))}</div>
                    </div>
                  </div>
                  <div class="chips">
                    <span class="chip">{escape(str(row.get('market') or '--'))}</span>
                    <span class="chip">觀察指標 {escape(str(row.get('metrics_to_track') or '--'))}</span>
                  </div>
                  <p>受惠邏輯：{escape(str(row.get('benefit_logic') or '--'))}</p>
                  <p>節目證據：{escape(str(row.get('evidence_from_episode') or '--'))}</p>
                  <p>催化劑：{escape(str(row.get('catalyst') or '--'))}</p>
                  <p>風險：{escape(str(row.get('risk') or '--'))}</p>
                </article>
                """
            )
        return "".join(parts)

    def watchlist_cards():
        if not watch_cards:
            return '<p class="empty">目前沒有自選股。</p>'
        return "".join(
            f"""
            <article class="card">
              <div class="row">
                <div>
                  <div class="title">{escape(str(item.get('name') or item.get('code') or '--'))}</div>
                  <div class="subtle">{escape(str(item.get('code') or '--'))}</div>
                </div>
                <div class="price-block">
                  <div class="price">{escape(str(item.get('price') or '--'))}</div>
                  <div class="{escape(str(item.get('trend_class') or 'flat'))}">{escape(str(item.get('trend_value') or '--'))}</div>
                </div>
              </div>
              <div class="chips">
                <span class="chip">昨收 {escape(str(item.get('previous_close') or '--'))}</span>
                <span class="chip">{escape(str(item.get('sell_level') or '--'))}</span>
                <span class="chip">更新 {escape(str(item.get('updated') or '--'))}</span>
              </div>
              <p>{escape(str(item.get('sell_message') or '--'))}</p>
            </article>
            """
            for item in watch_cards
        )

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>台股精選手機快照</title>
  <style>
    :root {{ --bg:#f4f1ea; --panel:#fff; --text:#1f2933; --muted:#5f6b76; --border:#ddd6c8; --up:#c0392b; --down:#1f8a5c; --flat:#6b7280; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.65 "Microsoft JhengHei UI", sans-serif; }}
    main {{ max-width:920px; margin:0 auto; padding:14px; display:grid; gap:14px; }}
    section {{ background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:16px; }}
    h1, h2, h3, p {{ margin:0; }}
    h1 {{ font-size:28px; }}
    h2 {{ font-size:20px; margin-bottom:8px; }}
    .subtle {{ color:var(--muted); font-size:13px; }}
    .stack {{ display:grid; gap:10px; }}
    .row {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }}
    .title {{ font-size:18px; font-weight:800; }}
    .price-block {{ text-align:right; }}
    .price {{ font-size:24px; font-weight:900; }}
    .chips {{ display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }}
    .chip {{ border:1px solid var(--border); border-radius:999px; padding:4px 10px; background:#faf7f2; font-size:12px; }}
    .empty-chip {{ color:var(--muted); }}
    .up {{ color:var(--up); }}
    .down {{ color:var(--down); }}
    .flat {{ color:var(--flat); }}
    .grid {{ display:grid; gap:10px; }}
    .card {{ border:1px solid var(--border); border-radius:12px; padding:12px; background:#fffdfa; }}
    .hero {{ background:#eef4f1; }}
    .empty {{ color:var(--muted); }}
    @media (max-width: 768px) {{
      main {{ padding:10px; }}
      .row {{ display:grid; }}
      .price-block {{ text-align:left; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero stack">
      <div class="subtle">手機離線快照</div>
      <h1>台股精選前次結果</h1>
      <p class="subtle">技術面日期 {snapshot_date} / 分析成功 {analyzed_count} 檔 / 分析失敗 {failed_count} 檔</p>
      <p class="subtle">快照建立時間 {generated_at}</p>
    </section>

    <section class="stack">
      <h2>技術面</h2>
      <div class="grid">{stock_cards()}</div>
    </section>

    <section class="stack">
      <h2>新聞面</h2>
      <p>{escape(str(analysis.get('summary') or '目前沒有新聞面摘要。'))}</p>
      <h3>核心話題</h3>
      <div class="grid">{topic_cards()}</div>
      <h3>重點新聞</h3>
      <div class="grid">{news_cards()}</div>
      <h3>連動個股</h3>
      <div class="grid">{company_cards()}</div>
    </section>

    <section class="stack">
      <h2>股癌</h2>
      <div class="chips">
        <span class="chip">本次訊號來源：{escape(podcast_sections['source'])}</span>
        <span class="chip">節目：{escape(str((podcast_meta or {}).get('episode') or '--'))}</span>
      </div>
      <p>{escape(str((podcast_meta or {}).get('summary') or '目前沒有股癌摘要。'))}</p>
      <h3>主題分類</h3>
      <div class="chips">{chips(podcast_sections['main_themes'])}</div>
      <h3>提及產業</h3>
      <div class="chips">{chips(podcast_sections['industries'])}</div>
      <h3>候選公司</h3>
      <div class="chips">{chips(podcast_sections['stock_candidates'])}</div>
      <h3>推薦結果</h3>
      <div class="grid">{podcast_cards()}</div>
    </section>

    <section class="stack">
      <h2>自選股追蹤</h2>
      <div class="grid">{watchlist_cards()}</div>
    </section>
  </main>
</body>
</html>"""


def save_mobile_offline_snapshot(snapshot_payload, watchlist_data, podcast_meta, podcast_rows, analysis_payload):
    try:
        html = render_mobile_offline_snapshot(snapshot_payload, watchlist_data, podcast_meta, podcast_rows, analysis_payload)
        MOBILE_SNAPSHOT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        GITHUB_PAGES_DIR.mkdir(parents=True, exist_ok=True)
        MOBILE_OFFLINE_SNAPSHOT_PATH.write_text(html, encoding="utf-8")
        MOBILE_OFFLINE_PUBLIC_PATH.write_text(html, encoding="utf-8")
        GITHUB_PAGES_INDEX_PATH.write_text(html, encoding="utf-8")
        GITHUB_PAGES_404_PATH.write_text(html, encoding="utf-8")
        GITHUB_PAGES_LATEST_PATH.write_text(html, encoding="utf-8")
        GITHUB_PAGES_NOJEKYLL_PATH.write_text("", encoding="utf-8")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = MOBILE_SNAPSHOT_ARCHIVE_DIR / f"mobile_snapshot_{timestamp}.html"
        archive_path.write_text(html, encoding="utf-8")
        archives = sorted(MOBILE_SNAPSHOT_ARCHIVE_DIR.glob("mobile_snapshot_*.html"), key=lambda item: item.stat().st_mtime, reverse=True)
        for old_path in archives[20:]:
            try:
                old_path.unlink()
            except OSError:
                pass
    except OSError:
        pass


def build_cached_revenue_growth_map():
    cache = load_json_payload(BASE_DIR / "monthly_revenue_cache.json")
    if not isinstance(cache, dict):
        return {}
    per_code = {}
    for ym in sorted(cache.keys())[-3:]:
        rows = cache.get(ym, {})
        if not isinstance(rows, dict):
            continue
        for code, payload in rows.items():
            if not isinstance(payload, dict):
                continue
            per_code.setdefault(str(code), []).append(
                {
                    "yoy": to_float(payload.get("yoy")),
                    "revenue": to_float(payload.get("revenue")),
                }
            )

    result = {}
    for code, values in per_code.items():
        growths = [item["yoy"] for item in values if item.get("yoy") is not None]
        revenues = [item["revenue"] for item in values if item.get("revenue") is not None]
        if not growths and not revenues:
            continue
        result[code] = {
            "growths_3m": growths[-3:],
            "revenues_3m": revenues[-3:],
            "avg_growth_3m": sum(growths[-3:]) / len(growths[-3:]) if growths else None,
            "all_growth_over_10": bool(growths and all(value > 10 for value in growths[-3:])),
            "revenue_rising_3m": bool(len(revenues) >= 3 and revenues[-3] < revenues[-2] < revenues[-1]),
        }
    return result


def rank_badge(index: int) -> str:
    if index < len(RANK_BADGES):
        return RANK_BADGES[index]
    return str(index + 1)


def rank_card_style(index: int):
    if index < len(RANK_CARD_STYLES):
        return RANK_CARD_STYLES[index]
    return CARD_BG, BORDER


class ScreenerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("台股精選推薦")
        self.root.geometry("1680x1020")
        self.root.minsize(1520, 940)
        self.root.configure(bg=PAGE_BG)

        self.status_var = tk.StringVar(value="準備中")
        self.mode_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.market_index_var = tk.StringVar(value="台股大盤指數 --")
        self.market_index_detail_var = tk.StringVar(value="等待讀取最新官方收盤價")
        self.watch_status_var = tk.StringVar(value="尚未更新自選股")
        self.analysis_status_var = tk.StringVar(value="每日分析：啟動後自動產生")
        self.analysis_update_var = tk.StringVar(value="新聞分析：等待最新快照")
        self.podcast_status_var = tk.StringVar(value="股癌逐字稿分析：等待執行")
        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.auto_refresh_status_var = tk.StringVar(value="報價刷新：手動")
        self.fundamental_refresh_var = tk.BooleanVar(value=False)
        self.fundamental_refresh_status_var = tk.StringVar(value="收盤價：等待讀取最新官方收盤價")
        self.watch_input_var = tk.StringVar()

        self.dashboard = None
        self.card_frames = []
        self.analysis_card_frames = []
        self.loading = False
        self.analysis_loading = False
        self.podcast_loading = False
        self.podcast_input_window = None
        self.progress_after_id = None
        self.auto_refresh_after_id = None
        self.fundamental_refresh_after_id = None
        self.daily_analysis_after_id = None
        self.analysis_payload = None
        self.analysis_report_text = ""
        self.podcast_rows = load_podcast_recommendations()
        self.podcast_meta = load_podcast_report_meta()

        self.watchlist_data = load_watchlist_data()
        self.watch_rows = []
        self.candidate_map = {}
        self.gui_snapshot = load_json_payload(GUI_SNAPSHOT_PATH)

        self._configure_style()
        self._build()
        self._render_watchlist_table()
        snapshot_loaded = self._restore_cached_snapshot()
        if not snapshot_loaded:
            self.root.after(120, lambda: self.run_async(force_refresh=False))
        self.root.after(1600, lambda: self.run_daily_analysis_async(scheduled=True))

    @staticmethod
    def _readonly_text(_event=None):
        return "break"

    def _configure_style(self) -> None:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure(".", font=("Microsoft JhengHei UI", 10))
        style.configure("Title.TLabel", font=("Microsoft JhengHei UI", 22, "bold"), foreground=TEXT_DARK, background=HEADER_BG)
        style.configure("Sub.TLabel", font=("Microsoft JhengHei UI", 10), foreground=TEXT_MID, background=HEADER_BG)
        style.configure("Panel.TLabelframe", background=PANEL_BG)
        style.configure("Panel.TLabelframe.Label", font=("Microsoft JhengHei UI", 11, "bold"), foreground=TEXT_DARK)
        style.configure("Treeview.Heading", font=("Microsoft JhengHei UI", 10, "bold"))

    def _bind_mousewheel(self, widget, callback) -> None:
        widget.bind("<Enter>", lambda _e: widget.bind_all("<MouseWheel>", callback))
        widget.bind("<Leave>", lambda _e: widget.unbind_all("<MouseWheel>"))

    def _build(self) -> None:
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self.root, bg=HEADER_BG, padx=14, pady=12)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(header, text="台股精選推薦", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status_var, style="Sub.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        tk.Label(header, textvariable=self.mode_var, bg=HEADER_BG, fg=TEXT_MID, font=("Microsoft JhengHei UI", 10)).grid(row=2, column=0, sticky="w", pady=(6, 0))
        button_wrap = tk.Frame(header, bg=HEADER_BG)
        button_wrap.grid(row=0, column=1, sticky="e")
        ttk.Button(button_wrap, text="刷新今天股價", command=self.refresh_today_prices).pack(side="left", padx=(0, 8))
        ttk.Button(button_wrap, text="複製推薦清單", command=self.copy_table).pack(side="left")
        tk.Label(
            header,
            textvariable=self.fundamental_refresh_status_var,
            bg=HEADER_BG,
            fg=TEXT_MID,
            font=("Microsoft JhengHei UI", 9),
        ).grid(row=2, column=1, sticky="e", pady=(6, 0))

        market_panel = tk.Frame(self.root, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=10)
        market_panel.grid(row=1, column=0, sticky="ew", padx=14, pady=(10, 0))
        market_panel.grid_columnconfigure(1, weight=1)
        tk.Label(
            market_panel,
            text="台股大盤",
            bg=PANEL_BG,
            fg=TEXT_MID,
            font=("Microsoft JhengHei UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 14))
        self.market_index_label = tk.Label(
            market_panel,
            textvariable=self.market_index_var,
            bg=PANEL_BG,
            fg=TEXT_DARK,
            font=("Microsoft JhengHei UI", 16, "bold"),
        )
        self.market_index_label.grid(row=0, column=1, sticky="w")
        tk.Label(
            market_panel,
            textvariable=self.market_index_detail_var,
            bg=PANEL_BG,
            fg=TEXT_MID,
            font=("Microsoft JhengHei UI", 10),
        ).grid(row=0, column=2, sticky="e", padx=(16, 0))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=14, pady=(10, 14))

        self.recommend_tab = tk.Frame(self.notebook, bg=PAGE_BG)
        self.watchlist_tab = tk.Frame(self.notebook, bg=PAGE_BG)
        self.analysis_tab = tk.Frame(self.notebook, bg=PAGE_BG)
        self.podcast_tab = tk.Frame(self.notebook, bg=PAGE_BG)
        self.notebook.add(self.recommend_tab, text="技術面")
        self.notebook.add(self.analysis_tab, text="新聞面")
        self.notebook.add(self.podcast_tab, text="股癌")
        self.notebook.add(self.watchlist_tab, text="自選股追蹤")

        self._build_recommend_tab()
        self._build_analysis_tab()
        self._build_podcast_tab()
        self._build_watchlist_tab()

    def _save_gui_snapshot(self) -> None:
        self.gui_snapshot = build_gui_snapshot_payload(
            self.dashboard,
            self.watch_rows,
            str((self.gui_snapshot or {}).get("latest_close_date") or ""),
            int((self.gui_snapshot or {}).get("quote_updated") or 0),
            int((self.gui_snapshot or {}).get("quote_failed") or 0),
            (self.gui_snapshot or {}).get("market_index") if isinstance(self.gui_snapshot, dict) else {},
            str((self.gui_snapshot or {}).get("quote_date") or ""),
            self.analysis_payload,
            self.podcast_meta,
            self.podcast_rows,
        )
        try:
            GUI_SNAPSHOT_PATH.write_text(json.dumps(self.gui_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _export_mobile_snapshot(self) -> None:
        payload = self.gui_snapshot if isinstance(self.gui_snapshot, dict) else {}
        analysis_payload = self.analysis_payload
        if not isinstance(analysis_payload, dict) or not analysis_payload:
            analysis_payload = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
        podcast_block = payload.get("podcast") if isinstance(payload.get("podcast"), dict) else {}
        podcast_meta = self.podcast_meta or podcast_block.get("meta") or {}
        podcast_rows = self.podcast_rows or podcast_block.get("rows") or []
        save_mobile_offline_snapshot(payload, self.watchlist_data, podcast_meta, podcast_rows, analysis_payload)

    def _restore_cached_snapshot(self) -> bool:
        payload = self.gui_snapshot if isinstance(self.gui_snapshot, dict) else {}
        dashboard = payload.get("dashboard")
        if not isinstance(dashboard, dict) or not dashboard.get("top_stocks"):
            return False
        watch_rows = payload.get("watch_rows")
        if not isinstance(watch_rows, list):
            watch_rows = []
        if not watch_rows:
            watch_rows = build_watch_rows_from_history_payload(self.watchlist_data)
        latest_close_date = str(payload.get("latest_close_date") or "")
        quote_updated = int(payload.get("quote_updated") or 0)
        quote_failed = int(payload.get("quote_failed") or 0)
        market_index = payload.get("market_index")
        if not isinstance(market_index, dict):
            market_index = {}
        quote_date = str(payload.get("quote_date") or "")
        if isinstance(payload.get("analysis"), dict) and payload.get("analysis"):
            self.analysis_payload = payload.get("analysis")
        podcast_block = payload.get("podcast") if isinstance(payload.get("podcast"), dict) else {}
        if isinstance(podcast_block.get("meta"), dict) and podcast_block.get("meta"):
            self.podcast_meta = podcast_block.get("meta")
        if isinstance(podcast_block.get("rows"), list) and podcast_block.get("rows"):
            self.podcast_rows = podcast_block.get("rows")
        self._set_dashboard(
            dashboard,
            watch_rows,
            latest_close_date,
            quote_updated,
            quote_failed,
            market_index,
            quote_date,
            from_cache=True,
        )
        if isinstance(self.analysis_payload, dict) and self.analysis_payload:
            self.analysis_report_text = self.analysis_payload.get("report", "")
            self._render_daily_analysis(self.analysis_payload)
        self._render_podcast_tab()
        self._export_mobile_snapshot()
        return True

    def _build_recommend_tab(self) -> None:
        self.recommend_tab.grid_rowconfigure(2, weight=1)
        self.recommend_tab.grid_columnconfigure(0, weight=1)

        overview = tk.Frame(self.recommend_tab, bg=PAGE_BG)
        overview.grid(row=0, column=0, sticky="ew")
        overview.grid_columnconfigure(0, weight=1)
        overview.grid_columnconfigure(1, weight=1)

        left_panel = tk.Frame(overview, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=14)
        left_panel.grid(row=0, column=0, sticky="nsew")
        tk.Label(left_panel, text="固定條件", bg=PANEL_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 13, "bold")).pack(anchor="w")
        self.strategy_text = tk.Text(left_panel, height=9, wrap="word", font=("Microsoft JhengHei UI", 10), bg=PANEL_BG, fg=TEXT_DARK, relief="flat", bd=0)
        self.strategy_text.pack(fill="both", expand=True, pady=(6, 0))
        self.strategy_text.insert("1.0", "系統會自動套用固定條件，優先顯示完全通過必要條件的前 5 名股票；若正選不足 5 檔，則改顯示最接近條件但未通過的候補名單。\n\n")
        for line in strategy_lines():
            self.strategy_text.insert("end", f"• {line}\n")
        self.strategy_text.bind("<Key>", self._readonly_text)

        right_panel = tk.Frame(overview, bg=ACCENT_BG, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=14)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        tk.Label(right_panel, text="推薦結果的產業敘述", bg=ACCENT_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 13, "bold")).pack(anchor="w")
        summary_wrap = tk.Frame(right_panel, bg=ACCENT_BG)
        summary_wrap.pack(fill="both", expand=True, pady=(6, 0))
        summary_scroll = ttk.Scrollbar(summary_wrap, orient="vertical")
        self.summary_text = tk.Text(
            summary_wrap,
            height=9,
            wrap="word",
            font=("Microsoft JhengHei UI", 10),
            bg=ACCENT_BG,
            fg=TEXT_DARK,
            relief="flat",
            bd=0,
            yscrollcommand=summary_scroll.set,
            cursor="arrow",
        )
        summary_scroll.configure(command=self.summary_text.yview)
        self.summary_text.pack(side="left", fill="both", expand=True)
        summary_scroll.pack(side="right", fill="y")
        self.summary_text.bind("<Key>", self._readonly_text)
        self._bind_mousewheel(self.summary_text, lambda e: self.summary_text.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self._set_summary("載入中，請稍候。", [])

        cards_panel = ttk.LabelFrame(self.recommend_tab, text="前 5 名精選股大卡片", style="Panel.TLabelframe", padding=10)
        cards_panel.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        cards_panel.grid_columnconfigure(0, weight=1)
        self.card_container = tk.Frame(cards_panel, bg=PANEL_BG)
        self.card_container.grid(row=0, column=0, sticky="ew")

        table_panel = ttk.LabelFrame(self.recommend_tab, text="推薦清單", style="Panel.TLabelframe", padding=10)
        table_panel.grid(row=2, column=0, sticky="nsew")
        table_panel.grid_columnconfigure(0, weight=1)
        table_panel.grid_rowconfigure(1, weight=1)

        table_head = tk.Frame(table_panel, bg=PANEL_BG)
        table_head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(table_head, text="複製選取列", command=self.copy_selected_row).pack(side="right")
        ttk.Button(table_head, text="複製整個清單", command=self.copy_table).pack(side="right", padx=(0, 8))

        columns = ("排名", "代號", "名稱", "股價", "漲跌", "推薦分數", "條件符合", "EPS 年增", "3 月平均 YoY", "ROE", "20 日漲幅")
        self.tree = ttk.Treeview(table_panel, columns=columns, show="headings", height=4)
        widths = (92, 72, 180, 92, 92, 110, 100, 90, 110, 76, 92)
        for col, width in zip(columns, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")
        self.tree.tag_configure("up", foreground=UP_COLOR)
        self.tree.tag_configure("down", foreground=DOWN_COLOR)
        self.tree.tag_configure("flat", foreground=FLAT_COLOR)
        self.tree.tag_configure("rank_gold", background="#fff7df")
        self.tree.tag_configure("rank_silver", background="#f3f4f6")
        self.tree.tag_configure("rank_bronze", background="#fff1e7")
        self.tree.bind("<Double-1>", lambda _e: self.copy_selected_row())
        tree_scroll = ttk.Scrollbar(table_panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        tree_scroll.grid(row=1, column=1, sticky="ns")

    def _build_watchlist_tab(self) -> None:
        self.watchlist_tab.grid_rowconfigure(1, weight=1)
        self.watchlist_tab.grid_columnconfigure(0, weight=1)

        controls = tk.Frame(self.watchlist_tab, bg=PAGE_BG)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.grid_columnconfigure(1, weight=1)

        tk.Label(controls, text="輸入自選股代號", bg=PAGE_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(controls, textvariable=self.watch_input_var)
        entry.grid(row=0, column=1, sticky="ew", padx=(10, 10))
        entry.bind("<Return>", lambda _e: self.add_watchlist_stock())
        ttk.Button(controls, text="加入自選股", command=self.add_watchlist_stock).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(controls, text="刪除選取", command=self.delete_watchlist_stock).grid(row=0, column=3, padx=(0, 8))
        tk.Label(controls, textvariable=self.watch_status_var, bg=PAGE_BG, fg=TEXT_MID, font=("Microsoft JhengHei UI", 10)).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))

        body = tk.Frame(self.watchlist_tab, bg=PAGE_BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        watch_panel = ttk.LabelFrame(body, text="自選股每日追蹤", style="Panel.TLabelframe", padding=10)
        watch_panel.grid(row=0, column=0, sticky="nsew")
        watch_panel.grid_columnconfigure(0, weight=1)
        watch_panel.grid_rowconfigure(0, weight=1)

        watch_columns = ("代號", "名稱", "股價", "漲跌幅", "昨收", "賣出建議", "更新時間")
        self.watch_tree = ttk.Treeview(watch_panel, columns=watch_columns, show="headings", height=16, selectmode="browse")
        watch_widths = (80, 160, 100, 110, 100, 120, 110)
        for col, width in zip(watch_columns, watch_widths):
            self.watch_tree.heading(col, text=col)
            self.watch_tree.column(col, width=width, anchor="center")
        self.watch_tree.tag_configure("up", foreground=UP_COLOR)
        self.watch_tree.tag_configure("down", foreground=DOWN_COLOR)
        self.watch_tree.tag_configure("flat", foreground=FLAT_COLOR)
        self.watch_tree.tag_configure("sell_urgent", foreground=SELL_URGENT_COLOR)
        self.watch_tree.tag_configure("sell_watch", foreground=SELL_WATCH_COLOR)
        self.watch_tree.tag_configure("sell_ok", foreground=SELL_OK_COLOR)
        self.watch_tree.bind("<<TreeviewSelect>>", self._on_watchlist_select)
        watch_scroll = ttk.Scrollbar(watch_panel, orient="vertical", command=self.watch_tree.yview)
        self.watch_tree.configure(yscrollcommand=watch_scroll.set)
        self.watch_tree.grid(row=0, column=0, sticky="nsew")
        watch_scroll.grid(row=0, column=1, sticky="ns")

        history_panel = ttk.LabelFrame(body, text="賣出建議與追蹤紀錄", style="Panel.TLabelframe", padding=10)
        history_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        history_panel.grid_columnconfigure(0, weight=1)
        history_panel.grid_rowconfigure(1, weight=1)

        sell_wrap = tk.Frame(history_panel, bg=PANEL_BG)
        sell_wrap.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Label(sell_wrap, text="自選股賣出建議", bg=PANEL_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 11, "bold")).pack(anchor="w")
        self.watch_sell_text = tk.Text(
            sell_wrap,
            height=10,
            wrap="word",
            font=("Microsoft JhengHei UI", 10),
            bg=PANEL_BG,
            fg=TEXT_DARK,
            relief="flat",
            bd=0,
        )
        self.watch_sell_text.pack(fill="both", expand=True, pady=(6, 0))
        self.watch_sell_text.bind("<Key>", self._readonly_text)
        self.watch_sell_text.insert("1.0", "請先在左側選取一檔自選股，系統會依照技術面與基本面規則顯示賣出建議。")

        history_wrap = tk.Frame(history_panel, bg=PANEL_BG)
        history_wrap.grid(row=1, column=0, sticky="nsew")
        history_scroll = ttk.Scrollbar(history_wrap, orient="vertical")
        self.watch_history_text = tk.Text(
            history_wrap,
            wrap="word",
            font=("Microsoft JhengHei UI", 10),
            bg=PANEL_BG,
            fg=TEXT_DARK,
            relief="flat",
            bd=0,
            yscrollcommand=history_scroll.set,
        )
        history_scroll.configure(command=self.watch_history_text.yview)
        self.watch_history_text.pack(side="left", fill="both", expand=True)
        history_scroll.pack(side="right", fill="y")
        self.watch_history_text.bind("<Key>", self._readonly_text)
        self.watch_history_text.insert("1.0", "請先在左側加入自選股，系統會保留清單並記錄每日更新價格。")

    def _build_analysis_tab(self) -> None:
        self.analysis_tab.grid_rowconfigure(3, weight=1)
        self.analysis_tab.grid_columnconfigure(0, weight=1)

        controls = tk.Frame(self.analysis_tab, bg=PAGE_BG)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.grid_columnconfigure(3, weight=1)
        ttk.Button(controls, text="立即重新分析", command=self.run_daily_analysis_async).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(controls, text="複製完整報告", command=self.copy_daily_analysis).grid(row=0, column=1, padx=(0, 12))
        tk.Label(
            controls,
            textvariable=self.analysis_status_var,
            bg=PAGE_BG,
            fg=TEXT_MID,
            font=("Microsoft JhengHei UI", 10),
        ).grid(row=0, column=2, sticky="w")
        tk.Label(
            controls,
            textvariable=self.analysis_update_var,
            bg=PAGE_BG,
            fg=TEXT_MID,
            font=("Microsoft JhengHei UI", 9),
        ).grid(row=0, column=3, sticky="e")

        overview = tk.Frame(self.analysis_tab, bg=PAGE_BG)
        overview.grid(row=1, column=0, sticky="ew")
        overview.grid_columnconfigure(0, weight=2)
        overview.grid_columnconfigure(1, weight=1)

        signal_panel = tk.Frame(overview, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=12)
        signal_panel.grid(row=0, column=0, sticky="nsew")
        tk.Label(signal_panel, text="今日市場訊號", bg=PANEL_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 13, "bold")).pack(anchor="w")
        self.analysis_summary_text = tk.Text(signal_panel, height=4, wrap="word", font=("Microsoft JhengHei UI", 10), bg=PANEL_BG, fg=TEXT_DARK, relief="flat", bd=0)
        self.analysis_summary_text.pack(fill="both", expand=True, pady=(6, 0))
        self.analysis_summary_text.insert("1.0", "每日分析會在啟動後自動產生，並寫入手機可讀快照。")
        self.analysis_summary_text.bind("<Key>", self._readonly_text)

        pulse_panel = tk.Frame(overview, bg=ACCENT_BG, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=12)
        pulse_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        tk.Label(pulse_panel, text="更新節奏", bg=ACCENT_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 13, "bold")).pack(anchor="w")
        self.analysis_pulse_text = tk.Text(pulse_panel, height=4, wrap="word", font=("Microsoft JhengHei UI", 10), bg=ACCENT_BG, fg=TEXT_DARK, relief="flat", bd=0)
        self.analysis_pulse_text.pack(fill="both", expand=True, pady=(6, 0))
        self.analysis_pulse_text.insert("1.0", "新聞與供應鏈分析：啟動後自動產生\n價格：最新官方收盤價\n推薦：啟動後自動更新")
        self.analysis_pulse_text.bind("<Key>", self._readonly_text)

        cards_panel = ttk.LabelFrame(self.analysis_tab, text="核心熱門話題", style="Panel.TLabelframe", padding=10)
        cards_panel.grid(row=2, column=0, sticky="ew", pady=(10, 10))
        cards_panel.grid_columnconfigure(0, weight=1)
        self.analysis_card_container = tk.Frame(cards_panel, bg=PANEL_BG)
        self.analysis_card_container.grid(row=0, column=0, sticky="ew")

        body = tk.Frame(self.analysis_tab, bg=PAGE_BG)
        body.grid(row=3, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        news_panel = ttk.LabelFrame(body, text="市場影響新聞", style="Panel.TLabelframe", padding=10)
        news_panel.grid(row=0, column=0, sticky="nsew")
        news_panel.grid_columnconfigure(0, weight=1)
        news_panel.grid_rowconfigure(0, weight=1)
        news_columns = ("新聞重點", "影響層面", "來源", "時間")
        self.analysis_news_tree = ttk.Treeview(news_panel, columns=news_columns, show="headings", height=10)
        news_widths = (560, 130, 120, 90)
        for col, width in zip(news_columns, news_widths):
            self.analysis_news_tree.heading(col, text=col)
            self.analysis_news_tree.column(col, width=width, anchor="w" if col == "新聞重點" else "center")
        self.analysis_news_tree.tag_configure("hot", foreground=UP_COLOR)
        self.analysis_news_tree.bind("<Double-1>", self.open_selected_analysis_news)
        news_scroll = ttk.Scrollbar(news_panel, orient="vertical", command=self.analysis_news_tree.yview)
        self.analysis_news_tree.configure(yscrollcommand=news_scroll.set)
        self.analysis_news_tree.grid(row=0, column=0, sticky="nsew")
        news_scroll.grid(row=0, column=1, sticky="ns")

        company_panel = ttk.LabelFrame(body, text="台股供應鏈受惠名單", style="Panel.TLabelframe", padding=10)
        company_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        company_panel.grid_columnconfigure(0, weight=1)
        company_panel.grid_rowconfigure(0, weight=1)
        company_columns = ("排名", "公司", "受惠", "連結主題")
        self.analysis_company_tree = ttk.Treeview(company_panel, columns=company_columns, show="headings", height=10)
        company_widths = (82, 110, 70, 260)
        for col, width in zip(company_columns, company_widths):
            self.analysis_company_tree.heading(col, text=col)
            self.analysis_company_tree.column(col, width=width, anchor="center" if col != "連結主題" else "w")
        self.analysis_company_tree.tag_configure("rank_gold", background="#fff7df")
        self.analysis_company_tree.tag_configure("rank_silver", background="#f3f4f6")
        self.analysis_company_tree.tag_configure("rank_bronze", background="#fff1e7")
        company_scroll = ttk.Scrollbar(company_panel, orient="vertical", command=self.analysis_company_tree.yview)
        self.analysis_company_tree.configure(yscrollcommand=company_scroll.set)
        self.analysis_company_tree.grid(row=0, column=0, sticky="nsew")
        company_scroll.grid(row=0, column=1, sticky="ns")

    def _build_podcast_tab(self) -> None:
        self.podcast_tab.grid_rowconfigure(2, weight=1)
        self.podcast_tab.grid_columnconfigure(0, weight=1)

        controls = tk.Frame(self.podcast_tab, bg=PAGE_BG)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.grid_columnconfigure(2, weight=1)
        ttk.Button(controls, text="輸入集數一鍵分析", command=self.run_podcast_from_query_dialog).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Button(controls, text="重新讀取股癌結果", command=self.reload_podcast_tab).grid(row=0, column=1, sticky="w")
        tk.Label(
            controls,
            textvariable=self.podcast_status_var,
            bg=PAGE_BG,
            fg=TEXT_MID,
            font=("Microsoft JhengHei UI", 10),
        ).grid(row=0, column=2, sticky="e")

        top = tk.Frame(self.podcast_tab, bg=PAGE_BG)
        top.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        top.grid_columnconfigure(0, weight=2)
        top.grid_columnconfigure(1, weight=3)
        top.grid_columnconfigure(2, weight=3)

        meta_panel = tk.Frame(top, bg=ACCENT_BG, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=12)
        meta_panel.grid(row=0, column=0, sticky="nsew")
        tk.Label(meta_panel, text="股癌最新節目", bg=ACCENT_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 13, "bold")).pack(anchor="w")
        self.podcast_meta_text = tk.Text(meta_panel, height=6, wrap="word", font=("Microsoft JhengHei UI", 10), bg=ACCENT_BG, fg=TEXT_DARK, relief="flat", bd=0)
        self.podcast_meta_text.pack(fill="both", expand=True, pady=(6, 0))
        self.podcast_meta_text.bind("<Key>", self._readonly_text)

        summary_panel = tk.Frame(top, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=12)
        summary_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        tk.Label(summary_panel, text="本集摘要", bg=PANEL_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 13, "bold")).pack(anchor="w")
        self.podcast_summary_text = tk.Text(summary_panel, height=6, wrap="word", font=("Microsoft JhengHei UI", 10), bg=PANEL_BG, fg=TEXT_DARK, relief="flat", bd=0)
        self.podcast_summary_text.pack(fill="both", expand=True, pady=(6, 0))
        self.podcast_summary_text.bind("<Key>", self._readonly_text)

        signal_panel = tk.Frame(top, bg=ACCENT_BG, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=12)
        signal_panel.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        tk.Label(signal_panel, text="LLM 主題拆解", bg=ACCENT_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 13, "bold")).pack(anchor="w")
        self.podcast_signal_text = tk.Text(signal_panel, height=6, wrap="word", font=("Microsoft JhengHei UI", 10), bg=ACCENT_BG, fg=TEXT_DARK, relief="flat", bd=0)
        self.podcast_signal_text.pack(fill="both", expand=True, pady=(6, 0))
        self.podcast_signal_text.bind("<Key>", self._readonly_text)

        body = ttk.LabelFrame(self.podcast_tab, text="股癌推薦結果", style="Panel.TLabelframe", padding=10)
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        columns = ("排名", "代號", "公司", "產業", "股價", "信心分數", "受惠邏輯", "節目證據", "催化劑", "風險", "觀察指標")
        self.podcast_tree = ttk.Treeview(body, columns=columns, show="headings", height=16)
        widths = (60, 80, 120, 110, 80, 80, 260, 260, 180, 180, 180)
        for col, width in zip(columns, widths):
            self.podcast_tree.heading(col, text=col)
            self.podcast_tree.column(col, width=width, anchor="center" if col in {"排名", "代號", "股價", "信心分數"} else "w")
        podcast_scroll = ttk.Scrollbar(body, orient="vertical", command=self.podcast_tree.yview)
        self.podcast_tree.configure(yscrollcommand=podcast_scroll.set)
        self.podcast_tree.grid(row=0, column=0, sticky="nsew")
        podcast_scroll.grid(row=0, column=1, sticky="ns")
        self._render_podcast_tab()

    def reload_podcast_tab(self) -> None:
        self.podcast_rows = load_podcast_recommendations()
        self.podcast_meta = load_podcast_report_meta()
        self._render_podcast_tab()
        self._save_gui_snapshot()
        self._export_mobile_snapshot()
        self.status_var.set("股癌推薦結果已重新讀取")
        self.podcast_status_var.set("股癌頁已重新讀取最新輸出")

    def run_podcast_project_async(self) -> None:
        if self.podcast_loading:
            self.podcast_status_var.set("股癌逐字稿分析正在執行中，請稍候...")
            return
        if not PODCAST_PROJECT_DIR.exists():
            messagebox.showerror("找不到專案", f"找不到資料夾：{PODCAST_PROJECT_DIR}")
            return
        episode_files = [
            path for path in (PODCAST_PROJECT_DIR / "episodes").glob("*")
            if path.is_file()
            and path.suffix.lower() in {".txt", ".md", ".json"}
            and ".example" not in path.name.lower()
        ]
        if not episode_files:
            messagebox.showwarning(
                "缺少逐字稿",
                "目前還沒有可分析的逐字稿。\n"
                f"請先把 .txt、.md 或 .json 檔放進：\n{PODCAST_PROJECT_DIR / 'episodes'}"
            )
            self.podcast_status_var.set("請先放入逐字稿檔案")
            return
        self.podcast_loading = True
        self.status_var.set("正在執行股癌逐字稿分析...")
        self.podcast_status_var.set("股癌逐字稿分析執行中...")
        threading.Thread(target=self._podcast_project_worker, args=(["main.py"], time.time()), daemon=True).start()

    def run_podcast_from_query_dialog(self) -> None:
        if self.podcast_loading:
            self.podcast_status_var.set("股癌逐字稿分析正在執行中，請稍候...")
            return
        query = simpledialog.askstring(
            "輸入集數或網址",
            "請輸入集數、標題關鍵字，或直接貼上該集網址。\n例如：EP672",
            parent=self.root,
        )
        if not query or not query.strip():
            return
        self.run_podcast_project_from_query(query.strip())

    def run_podcast_project_from_query(self, query: str) -> None:
        if not PODCAST_PROJECT_DIR.exists():
            messagebox.showerror("找不到專案", f"找不到資料夾：{PODCAST_PROJECT_DIR}")
            return
        self.podcast_loading = True
        self.status_var.set("正在依集數 / 網址自動抓取股癌節目...")
        self.podcast_status_var.set(f"正在自動分析：{query}")
        threading.Thread(
            target=self._podcast_project_worker,
            args=(["main.py", "--episode-query", query], time.time()),
            daemon=True,
        ).start()

    def ensure_podcast_api_key(self) -> bool:
        existing = os.environ.get("OPENAI_API_KEY", "").strip()
        if existing:
            return True
        if PODCAST_ENV_PATH.exists():
            try:
                text = PODCAST_ENV_PATH.read_text(encoding="utf-8")
            except OSError:
                text = ""
            for line in text.splitlines():
                if line.strip().startswith("OPENAI_API_KEY="):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if value:
                        os.environ["OPENAI_API_KEY"] = value
                        return True

        api_key = simpledialog.askstring(
            "輸入 OpenAI API Key",
            "第一次使用需要輸入 OpenAI API key。\n輸入後會自動存到 podcast_llm_project/.env，之後不用再填。",
            parent=self.root,
        )
        if not api_key or not api_key.strip():
            self.podcast_status_var.set("未輸入 OpenAI API key")
            return False
        clean_key = api_key.strip()
        try:
            lines = []
            if PODCAST_ENV_PATH.exists():
                try:
                    lines = PODCAST_ENV_PATH.read_text(encoding="utf-8").splitlines()
                except OSError:
                    lines = []
            updated = []
            replaced = False
            for line in lines:
                if line.strip().startswith("OPENAI_API_KEY="):
                    updated.append(f"OPENAI_API_KEY={clean_key}")
                    replaced = True
                else:
                    updated.append(line)
            if not replaced:
                updated.append(f"OPENAI_API_KEY={clean_key}")
            PODCAST_ENV_PATH.write_text("\n".join(updated).strip() + "\n", encoding="utf-8")
            os.environ["OPENAI_API_KEY"] = clean_key
            self.podcast_status_var.set("已儲存 OpenAI API key")
            return True
        except OSError as exc:
            messagebox.showerror("儲存 API key 失敗", str(exc))
            return False

    def open_podcast_episode_folder(self) -> None:
        episode_dir = PODCAST_PROJECT_DIR / "episodes"
        episode_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["explorer", str(episode_dir)])
            self.podcast_status_var.set("已開啟逐字稿資料夾")
        except Exception as exc:
            messagebox.showerror("開啟資料夾失敗", str(exc))

    def create_podcast_episode_template(self) -> None:
        episode_dir = PODCAST_PROJECT_DIR / "episodes"
        episode_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        template_path = episode_dir / f"episode_{timestamp}.txt"
        template_text = (
            f"episode_id: EP{timestamp}\n"
            "title: 請填入本集標題\n"
            f"date: {date.today().isoformat()}\n"
            "---\n"
            "請把這裡換成股癌 Podcast 的逐字稿全文。\n"
            "可以直接貼完整逐字稿，不用保留時間戳。\n"
        )
        try:
            template_path.write_text(template_text, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("建立範本失敗", str(exc))
            return
        self.podcast_status_var.set(f"已建立逐字稿範本：{template_path.name}")
        self.open_podcast_episode_folder()

    def open_podcast_input_dialog(self) -> None:
        if self.podcast_input_window and self.podcast_input_window.winfo_exists():
            self.podcast_input_window.lift()
            self.podcast_input_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title("直接貼上股癌逐字稿")
        window.geometry("980x760")
        window.minsize(860, 680)
        window.configure(bg=PAGE_BG)
        window.transient(self.root)
        self.podcast_input_window = window

        container = tk.Frame(window, bg=PAGE_BG, padx=16, pady=16)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(4, weight=1)

        episode_id_var = tk.StringVar(value=f"EP{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        title_var = tk.StringVar(value="")
        date_var = tk.StringVar(value=date.today().isoformat())

        tk.Label(container, text="集數 ID", bg=PAGE_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(container, textvariable=episode_id_var).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        tk.Label(container, text="節目標題", bg=PAGE_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(container, textvariable=title_var).grid(row=1, column=1, sticky="ew", pady=(0, 8))

        tk.Label(container, text="日期", bg=PAGE_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(container, textvariable=date_var).grid(row=2, column=1, sticky="ew", pady=(0, 8))

        tk.Label(container, text="逐字稿內容", bg=PAGE_BG, fg=TEXT_DARK, font=("Microsoft JhengHei UI", 10, "bold")).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 8))
        text_wrap = tk.Frame(container, bg=PAGE_BG)
        text_wrap.grid(row=4, column=0, columnspan=2, sticky="nsew")
        text_wrap.grid_columnconfigure(0, weight=1)
        text_wrap.grid_rowconfigure(0, weight=1)
        text_box = tk.Text(text_wrap, wrap="word", font=("Microsoft JhengHei UI", 10), bg=PANEL_BG, fg=TEXT_DARK)
        text_scroll = ttk.Scrollbar(text_wrap, orient="vertical", command=text_box.yview)
        text_box.configure(yscrollcommand=text_scroll.set)
        text_box.grid(row=0, column=0, sticky="nsew")
        text_scroll.grid(row=0, column=1, sticky="ns")

        hint = (
            "直接把整集逐字稿貼在這裡即可。\n"
            "如果你只有節目摘要，也可以先貼摘要，但完整逐字稿的效果會更好。"
        )
        tk.Label(container, text=hint, bg=PAGE_BG, fg=TEXT_MID, justify="left", font=("Microsoft JhengHei UI", 9)).grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 10))

        action_bar = tk.Frame(container, bg=PAGE_BG)
        action_bar.grid(row=6, column=0, columnspan=2, sticky="e")
        ttk.Button(action_bar, text="關閉", command=window.destroy).pack(side="right")
        ttk.Button(
            action_bar,
            text="儲存並分析",
            command=lambda: self.save_pasted_podcast_and_run(window, episode_id_var.get(), title_var.get(), date_var.get(), text_box.get("1.0", "end")),
        ).pack(side="right", padx=(0, 8))

        window.protocol("WM_DELETE_WINDOW", self.close_podcast_input_dialog)

    def close_podcast_input_dialog(self) -> None:
        if self.podcast_input_window and self.podcast_input_window.winfo_exists():
            self.podcast_input_window.destroy()
        self.podcast_input_window = None

    def save_pasted_podcast_and_run(self, window, episode_id: str, title: str, date_text: str, transcript: str) -> None:
        clean_episode_id = "".join(ch for ch in str(episode_id).strip() if ch.isalnum() or ch in {"-", "_"})
        clean_title = str(title).strip()
        clean_date = str(date_text).strip()
        clean_transcript = str(transcript).strip()

        if not clean_episode_id:
            messagebox.showwarning("缺少集數", "請先填入集數 ID。")
            return
        if not clean_title:
            messagebox.showwarning("缺少標題", "請先填入節目標題。")
            return
        if not clean_date:
            messagebox.showwarning("缺少日期", "請先填入日期。")
            return
        if len(clean_transcript) < 50:
            messagebox.showwarning("逐字稿太短", "請貼上較完整的逐字稿內容後再分析。")
            return

        episode_dir = PODCAST_PROJECT_DIR / "episodes"
        episode_dir.mkdir(parents=True, exist_ok=True)
        target_path = episode_dir / f"{clean_episode_id}.txt"
        payload = (
            f"episode_id: {clean_episode_id}\n"
            f"title: {clean_title}\n"
            f"date: {clean_date}\n"
            "---\n"
            f"{clean_transcript}\n"
        )
        try:
            target_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("儲存逐字稿失敗", str(exc))
            return

        self.close_podcast_input_dialog()
        self.podcast_status_var.set(f"已儲存逐字稿：{target_path.name}")
        self.run_podcast_project_async()

    def _podcast_project_worker(self, command_args, started_at: float) -> None:
        try:
            completed = subprocess.run(
                [sys.executable, *command_args],
                cwd=str(PODCAST_PROJECT_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except Exception as exc:
            self.root.after(0, lambda: self._handle_podcast_project_error(str(exc)))
            return
        self.root.after(0, lambda: self._finish_podcast_project(completed.returncode, completed.stdout, completed.stderr, started_at))

    def _finish_podcast_project(self, returncode: int, stdout_text: str, stderr_text: str, started_at: float) -> None:
        self.podcast_loading = False
        stdout_text = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", stdout_text or "")
        stderr_text = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", stderr_text or "")
        if returncode != 0:
            detail = self._build_podcast_error_message(stderr_text or stdout_text)
            self._handle_podcast_project_error(detail)
            return
        output_csv = PODCAST_OUTPUT_DIR / "podcast_recommendations.csv"
        if (not output_csv.exists()) or output_csv.stat().st_mtime < started_at:
            detail = self._build_podcast_error_message("程式已執行完成，但沒有產出新的推薦結果。")
            self._handle_podcast_project_error(detail)
            return
        self.reload_podcast_tab()
        self.status_var.set("股癌逐字稿分析完成")
        self.podcast_status_var.set("股癌推薦結果已更新")

    def _handle_podcast_project_error(self, detail: str) -> None:
        self.podcast_loading = False
        self.status_var.set("股癌逐字稿分析失敗")
        self.podcast_status_var.set("股癌逐字稿分析失敗")
        messagebox.showerror("股癌逐字稿分析失敗", detail[:3000] if detail else "未知錯誤")

    @staticmethod
    def _build_podcast_error_message(detail: str) -> str:
        text = str(detail or "").strip()
        text = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", text)
        if not text:
            return "股癌分析失敗，原因不明。"
        if "OPENAI_API_KEY" in text:
            return "目前沒有設定 OpenAI API key，所以無法做音檔轉逐字稿。若 RSS 有摘要，系統會改用摘要；若連摘要都不足，就會失敗。"
        if "RSS 中找不到符合" in text:
            return "找不到你輸入的那一集，請確認集數或網址是否正確。"
        if "沒有拿到可用的逐字稿或摘要" in text:
            return "有找到該集，但沒有可用的逐字稿或摘要內容，所以無法分析。"
        if "沒有篩出符合條件的候選股" in text:
            return "有抓到節目內容，但這次沒有篩出符合條件的候選股，所以沒有新結果。"
        if "沒有產出新的推薦結果" in text:
            return "這次執行後沒有產出新的股癌推薦結果，可能是節目內容不足，或本次沒有符合條件的候選股。"
        if "找不到逐字稿檔案" in text:
            return "目前沒有可分析的逐字稿檔案。"
        return text

    def _render_podcast_tab(self) -> None:
        if hasattr(self, "podcast_tree"):
            for row_id in self.podcast_tree.get_children():
                self.podcast_tree.delete(row_id)

        meta_lines = [
            f"集數：{self.podcast_meta.get('episode_id') or '--'}",
            f"節目：{self.podcast_meta.get('episode') or '--'}",
            f"日期：{self.podcast_meta.get('published') or '--'}",
            f"本次訊號來源：{format_podcast_signal_source(self.podcast_meta.get('signal_source', 'rule'), self.podcast_meta.get('generation_mode', ''))}",
        ]
        self.podcast_meta_text.delete("1.0", "end")
        self.podcast_meta_text.insert("1.0", "\n".join(meta_lines))

        summary = self.podcast_meta.get("summary") or "目前沒有讀到股癌摘要，仍可直接參考下方推薦名單。"
        self.podcast_summary_text.delete("1.0", "end")
        self.podcast_summary_text.insert("1.0", summary)

        sections = podcast_signal_sections(self.podcast_meta or {})
        signal_lines = [
            f"本次訊號來源：{sections['source']}",
            f"主題分類：{'、'.join(sections['main_themes']) if sections['main_themes'] else '目前沒有'}",
            f"提及產業：{'、'.join(sections['industries']) if sections['industries'] else '目前沒有'}",
            f"候選公司：{'、'.join(sections['stock_candidates']) if sections['stock_candidates'] else '目前沒有'}",
        ]
        self.podcast_signal_text.delete("1.0", "end")
        self.podcast_signal_text.insert("1.0", "\n".join(signal_lines))

        if not self.podcast_rows:
            self.podcast_tree.insert("", tk.END, values=("", "", "尚未找到股癌推薦結果", "", "", "", "", "", "", "", "請先產生 podcast_output/podcast_recommendations.csv"))
            return

        for index, row in enumerate(self.podcast_rows, start=1):
            self.podcast_tree.insert(
                "",
                tk.END,
                values=(
                    row.get("rank", index),
                    row.get("ticker", ""),
                    row.get("company", ""),
                    row.get("industry", ""),
                    row.get("price", ""),
                    row.get("confidence_score", ""),
                    row.get("benefit_logic", ""),
                    row.get("evidence_from_episode", ""),
                    row.get("catalyst", ""),
                    row.get("risk", ""),
                    row.get("metrics_to_track", ""),
                ),
            )

    def _set_progress(self, value: float) -> None:
        value = max(0.0, min(100.0, value))
        self.progress_var.set(value)
        if hasattr(self, "progress_label"):
            self.progress_label.config(text=f"{int(value)}%")

    def _animate_progress(self) -> None:
        return

    def _copy_to_clipboard(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _set_summary(self, plain_text: str, link_items) -> None:
        self.summary_text.delete("1.0", "end")
        if not link_items:
            self.summary_text.insert("1.0", plain_text)
            return
        for index, item in enumerate(link_items):
            self.summary_text.insert("end", item["text"])
            if item.get("url"):
                self.summary_text.insert("end", "連結：")
                start = self.summary_text.index("end")
                label = item.get("label") or item["url"]
                self.summary_text.insert("end", label)
                end = self.summary_text.index("end")
                tag_name = f"link_{index}"
                self.summary_text.tag_add(tag_name, start, end)
                self.summary_text.tag_configure(tag_name, foreground=LINK_COLOR, underline=True)
                self.summary_text.tag_bind(tag_name, "<Button-1>", lambda _e, url=item["url"]: webbrowser.open_new_tab(url))
                self.summary_text.tag_bind(tag_name, "<Enter>", lambda _e: self.summary_text.config(cursor="hand2"))
                self.summary_text.tag_bind(tag_name, "<Leave>", lambda _e: self.summary_text.config(cursor="arrow"))
            self.summary_text.insert("end", "\n\n")

    def copy_selected_row(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self._copy_to_clipboard(" | ".join(str(value) for value in values))

    def copy_table(self) -> None:
        rows = []
        headers = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
        rows.append(" | ".join(headers))
        for row_id in self.tree.get_children():
            values = self.tree.item(row_id, "values")
            rows.append(" | ".join(str(value) for value in values))
        self._copy_to_clipboard("\n".join(rows))

    def copy_daily_analysis(self) -> None:
        text = (self.analysis_report_text or "").strip()
        if not text and hasattr(self, "analysis_summary_text"):
            text = self.analysis_summary_text.get("1.0", "end").strip()
        if text:
            self._copy_to_clipboard(text)
            self.analysis_status_var.set("分析內容已複製")

    def run_daily_analysis_async(self, scheduled: bool = False) -> None:
        if self.analysis_loading:
            return
        self.analysis_loading = True
        self.status_var.set("正在產生每日科技產業分析...")
        self.analysis_status_var.set("正在抓取最近 24 小時新聞並整理供應鏈...")
        threading.Thread(target=self._daily_analysis_worker, args=(scheduled,), daemon=True).start()

    def _daily_analysis_worker(self, scheduled: bool = False) -> None:
        try:
            payload = generate_daily_tech_dashboard()
        except Exception as exc:
            self.root.after(0, lambda: self._handle_analysis_error(exc, scheduled))
            return
        self.root.after(0, lambda: self._set_daily_analysis(payload))

    def _handle_analysis_error(self, exc: Exception, scheduled: bool = False) -> None:
        self.analysis_loading = False
        self.analysis_status_var.set(f"每日分析失敗：{exc}")
        self.analysis_update_var.set("新聞分析：5 分鐘後重試")
        self._schedule_daily_analysis_refresh(delay_ms=5 * 60 * 1000)
        if not scheduled:
            messagebox.showerror("每日分析失敗", str(exc))

    def _set_daily_analysis(self, payload: dict) -> None:
        self.analysis_loading = False
        self.analysis_payload = payload
        self.analysis_report_text = payload.get("report", "")
        self.status_var.set("每日分析完成")
        self.analysis_status_var.set("每日分析已自動更新，可複製完整報告")
        self._render_daily_analysis(payload)
        self._save_gui_snapshot()
        self._export_mobile_snapshot()
        self._schedule_daily_analysis_refresh()

    def _schedule_daily_analysis_refresh(self, delay_ms: int = DAILY_ANALYSIS_REFRESH_SECONDS * 1000) -> None:
        if self.daily_analysis_after_id is not None:
            self.root.after_cancel(self.daily_analysis_after_id)
        next_time = datetime.fromtimestamp(datetime.now().timestamp() + delay_ms / 1000).strftime("%H:%M:%S")
        self.analysis_update_var.set(f"新聞分析下次更新：{next_time}")
        self.daily_analysis_after_id = self.root.after(delay_ms, self._daily_analysis_tick)

    def _daily_analysis_tick(self) -> None:
        self.daily_analysis_after_id = None
        self.run_daily_analysis_async(scheduled=True)

    def _clear_analysis_cards(self) -> None:
        for frame in self.analysis_card_frames:
            frame.destroy()
        self.analysis_card_frames.clear()

    def _build_analysis_topic_card(self, index: int, topic: dict) -> None:
        card_bg, border_color = rank_card_style(index)
        card = tk.Frame(self.analysis_card_container, bg=card_bg, highlightbackground=border_color, highlightthickness=2 if index < 3 else 1, bd=0)
        card.grid(row=0, column=index, sticky="nsew", padx=6, pady=6)
        self.analysis_card_container.grid_columnconfigure(index, weight=1)

        text = tk.Text(card, height=9, wrap="word", font=("Microsoft JhengHei UI", 9), bg=card_bg, fg=TEXT_MID, relief="flat", bd=0)
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.tag_configure("rank", foreground=border_color, font=("Segoe UI Emoji", 13, "bold"))
        text.tag_configure("title", foreground=TEXT_DARK, font=("Microsoft JhengHei UI", 10, "bold"))
        text.tag_configure("hot", foreground=SELECTED_COLOR, font=("Microsoft JhengHei UI", 9, "bold"))
        text.insert("end", f"{rank_badge(index)}\n", "rank")
        text.insert("end", f"{topic.get('name', '')}\n", "title")
        text.insert("end", f"持續時間：{topic.get('duration', '-')}\n", "hot")
        text.insert("end", f"驅動：{topic.get('driver', '')}\n\n")
        text.insert("end", f"瓶頸：{topic.get('bottleneck', '')}")
        text.bind("<Key>", self._readonly_text)
        self.analysis_card_frames.append(card)

    def _render_daily_analysis(self, payload: dict) -> None:
        self._clear_analysis_cards()
        for tree in (self.analysis_news_tree, self.analysis_company_tree):
            for row_id in tree.get_children():
                tree.delete(row_id)

        topics = payload.get("topics", [])
        news_items = payload.get("news", [])
        companies = payload.get("companies", [])
        self.analysis_news_links = {}

        self.analysis_summary_text.delete("1.0", "end")
        self.analysis_summary_text.insert("1.0", payload.get("summary", ""))
        self.analysis_pulse_text.delete("1.0", "end")
        self.analysis_pulse_text.insert(
            "1.0",
            f"分析日期：{payload.get('date', '-')}\n新聞：{len(news_items)} 則\n核心話題：{len(topics)} 個\n台股名單：{len(companies)} 家",
        )

        for index, topic in enumerate(topics[:3]):
            self._build_analysis_topic_card(index, topic)

        for index, item in enumerate(news_items):
            iid = f"news_{index}"
            impacts = " / ".join(item.get("impacts") or [])
            self.analysis_news_tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(item.get("summary") or item.get("title", ""), impacts, item.get("source", ""), item.get("published", "")),
                tags=("hot",) if index < 3 else (),
            )
            self.analysis_news_links[iid] = item.get("url", "")

        for index, company in enumerate(companies):
            rank_tag = "rank_gold" if index == 0 else "rank_silver" if index == 1 else "rank_bronze" if index == 2 else None
            self.analysis_company_tree.insert(
                "",
                tk.END,
                values=(
                    rank_badge(index),
                    f"{company.get('name', '')} ({company.get('code', '')})",
                    company.get("degree", ""),
                    company.get("topics", ""),
                ),
                tags=(rank_tag,) if rank_tag else (),
            )

    def open_selected_analysis_news(self, _event=None) -> None:
        selection = self.analysis_news_tree.selection()
        if not selection:
            return
        url = getattr(self, "analysis_news_links", {}).get(selection[0])
        if url:
            webbrowser.open_new_tab(url)

    def toggle_auto_refresh(self) -> None:
        self.auto_refresh_var.set(False)
        if self.auto_refresh_after_id is not None:
            self.root.after_cancel(self.auto_refresh_after_id)
            self.auto_refresh_after_id = None
        self.auto_refresh_status_var.set("報價刷新：手動")

    def toggle_fundamental_refresh(self) -> None:
        self.fundamental_refresh_var.set(False)
        if self.fundamental_refresh_after_id is not None:
            self.root.after_cancel(self.fundamental_refresh_after_id)
            self.fundamental_refresh_after_id = None
        self.fundamental_refresh_status_var.set("收盤價：等待讀取最新官方收盤價")

    def _format_next_fundamental_time(self, delay_ms: int) -> str:
        next_time = datetime.now().timestamp() + delay_ms / 1000
        return datetime.fromtimestamp(next_time).strftime("%H:%M:%S")

    def _schedule_auto_refresh(self, immediate: bool = False) -> None:
        if self.auto_refresh_after_id is not None:
            self.root.after_cancel(self.auto_refresh_after_id)
            self.auto_refresh_after_id = None
        self.auto_refresh_var.set(False)
        self.auto_refresh_status_var.set("報價刷新：手動")

    def _schedule_fundamental_refresh(self, delay_ms: int = 0) -> None:
        if self.fundamental_refresh_after_id is not None:
            self.root.after_cancel(self.fundamental_refresh_after_id)
            self.fundamental_refresh_after_id = None
        self.fundamental_refresh_var.set(False)
        self.fundamental_refresh_status_var.set("收盤價：等待讀取最新官方收盤價")

    def _auto_refresh_tick(self) -> None:
        self.auto_refresh_after_id = None
        self.auto_refresh_var.set(False)

    def _fundamental_refresh_tick(self) -> None:
        self.fundamental_refresh_after_id = None
        self.fundamental_refresh_var.set(False)

    def refresh_realtime_async(self, auto: bool = False) -> None:
        self.auto_refresh_status_var.set("即時報價已停用，改讀取最新官方收盤價")
        self.run_async(force_refresh=True)

    def refresh_today_prices(self) -> None:
        if self.loading:
            self.status_var.set("目前正在更新中，請稍候...")
            return
        self.status_var.set("正在刷新今天股價與自選股價格...")
        self.fundamental_refresh_status_var.set("收盤價：重新讀取中")
        self.run_async(force_refresh=True)

    def run_async(self, force_refresh: bool = False, scheduled: bool = False) -> None:
        if self.loading:
            return
        self.loading = True
        if scheduled:
            self.status_var.set("正在讀取最新官方收盤價...")
            self.fundamental_refresh_status_var.set("收盤價：讀取中")
        else:
            self.status_var.set("正在讀取最新官方收盤價並更新推薦，請稍候...")
            self.fundamental_refresh_status_var.set("收盤價：讀取中")
        self._set_progress(0)
        if self.progress_after_id is not None:
            self.root.after_cancel(self.progress_after_id)
        self._animate_progress()
        threading.Thread(target=self._worker, args=(force_refresh, scheduled), daemon=True).start()

    def _worker(self, force_refresh: bool = False, scheduled: bool = False) -> None:
        try:
            history_map, latest_close_date = self._load_today_close_history()
            dashboard = build_preferred_dashboard(30, use_cache=not force_refresh)
            if force_refresh and dashboard.get("cache_fallback"):
                raise RuntimeError("今日推薦資料尚未重新計算完成，已拒絕使用舊快取推薦。")
            save_csv(TOP_RECOMMENDATIONS_CSV_PATH, dashboard.get("top_stocks", [])[:10])
            watch_rows = self._fetch_watchlist_rows([item.get("code") for item in self.watchlist_data.get("stocks", []) if item.get("code")])
            quote_updated, quote_failed, market_index, quote_date = self._fetch_latest_quotes(dashboard, watch_rows)
        except Exception as exc:
            self.root.after(0, lambda: self._handle_error(exc, show_dialog=not scheduled, scheduled=scheduled))
            return
        self.root.after(0, lambda: self._set_dashboard(dashboard, watch_rows, latest_close_date, quote_updated, quote_failed, market_index, quote_date))

    def _load_gui_universe(self, session):
        fallback_map = build_fallback_candidate_map()
        if fallback_map:
            self.candidate_map = fallback_map
            return list(fallback_map.values())
        try:
            universe = build_universe(session)
        except Exception:
            universe = []
        candidate_map = {item.code: item for item in universe if getattr(item, "code", None)}
        if not candidate_map:
            candidate_map = fallback_map
        self.candidate_map = candidate_map
        return list(candidate_map.values())

    def _load_today_close_history(self, session=None):
        if session is None:
            session = requests.Session()
            session.trust_env = False
            session.headers.update({"User-Agent": USER_AGENT})
        history_map = build_twse_history_map(session)
        latest_date = latest_history_date(history_map)
        if not latest_date:
            raise RuntimeError("尚未讀到官方收盤資料，請稍後再試。")
        return history_map, latest_date

    def _apply_quote_to_row(self, row: dict, quote: dict) -> bool:
        if not quote:
            return False
        updated = False
        for source_key, target_key in (
            ("price", "price"),
            ("previous_close", "previous_close"),
            ("price_change", "price_change"),
            ("price_change_pct", "price_change_pct"),
            ("last_volume", "last_volume"),
        ):
            if quote.get(source_key) is not None:
                row[target_key] = quote.get(source_key)
                updated = True
        if quote.get("quote_type"):
            row["quote_type"] = quote.get("quote_type")
        if quote.get("realtime_at"):
            row["realtime_at"] = quote.get("realtime_at")
        return updated

    def _fetch_latest_quotes(self, dashboard, watch_rows):
        quote_inputs = []
        if dashboard:
            for key in ("top_stocks", "passed_stocks", "fallback_stocks"):
                quote_inputs.extend(dashboard.get(key, [])[:30])
        quote_inputs.extend(watch_rows or [])
        quote_inputs.extend(self.watchlist_data.get("stocks", []))
        if not quote_inputs:
            return 0, 0, None, ""
        expected_codes = []
        for item in quote_inputs:
            if isinstance(item, dict):
                code = str(item.get("code") or "").strip()
            else:
                code = str(getattr(item, "code", "") or "").strip()
            if code:
                expected_codes.append(code)
        expected_codes = list(dict.fromkeys(expected_codes))
        with requests.Session() as session:
            session.trust_env = False
            session.headers.update({"User-Agent": USER_AGENT})
            try:
                market_index = fetch_market_index(session)
            except Exception:
                market_index = None
            quotes = fetch_realtime_quotes(session, quote_inputs)

        updated = 0
        seen_rows = set()
        if dashboard:
            for key in ("top_stocks", "passed_stocks", "fallback_stocks"):
                for row in dashboard.get(key, []):
                    row_id = id(row)
                    if row_id in seen_rows:
                        continue
                    seen_rows.add(row_id)
                    if self._apply_quote_to_row(row, quotes.get(row.get("code"))):
                        updated += 1

        rows_by_code = {row.get("code"): row for row in watch_rows}
        stock_names = {item.get("code"): item.get("name", item.get("code")) for item in self.watchlist_data.get("stocks", [])}
        for code, quote in quotes.items():
            if code in rows_by_code:
                if self._apply_quote_to_row(rows_by_code[code], quote):
                    updated += 1
            elif code in stock_names:
                watch_rows.append(
                    {
                        "code": code,
                        "name": stock_names.get(code, code),
                        "market": "",
                        "price": quote.get("price"),
                        "previous_close": quote.get("previous_close"),
                        "price_change": quote.get("price_change"),
                        "price_change_pct": quote.get("price_change_pct"),
                        "last_volume": quote.get("last_volume"),
                        "realtime_at": quote.get("realtime_at"),
                    }
                )
                updated += 1
        success_count = sum(1 for code in expected_codes if quotes.get(code))
        failed_count = max(0, len(expected_codes) - success_count)
        quote_date = date.today().isoformat() if success_count else ""
        return updated, failed_count, market_index, quote_date

    def _fetch_watchlist_rows(self, codes):
        clean_codes = [str(code).strip() for code in codes if str(code).strip()]
        if not clean_codes:
            return []
        config = default_config()
        with requests.Session() as session:
            session.trust_env = False
            session.headers.update({"User-Agent": USER_AGENT})
            self._load_gui_universe(session)
            candidates = [self.candidate_map[code] for code in clean_codes if code in self.candidate_map]
            if not candidates:
                return []
            history_map, _latest_date = self._load_today_close_history(session)
            financial_cache = load_json_payload(BASE_DIR / "official_financial_cache.json")
            financial_map = financial_cache.get("data", {}) if isinstance(financial_cache.get("data"), dict) else {}
            valuation_cache = load_json_payload(BASE_DIR / "twse_valuation_cache.json")
            valuation_map = valuation_cache.get("data", {}) if isinstance(valuation_cache.get("data"), dict) else {}
            revenue_map = build_cached_revenue_growth_map()
            if not financial_map:
                financial_map = build_official_financial_map(session, candidates)
            if not valuation_map:
                valuation_map = build_twse_valuation_map(session, candidates)
            if not revenue_map:
                revenue_map = build_avg_revenue_growth_map(session)
            rows = []
            for candidate in candidates:
                stock = fetch_stock_metrics_with_retry(
                    candidate,
                    config,
                    revenue_map,
                    history_map,
                    financial_map,
                    valuation_map,
                )
                if stock:
                    rows.append(stock)
            order = {code: index for index, code in enumerate(clean_codes)}
            rows.sort(key=lambda item: order.get(item["code"], 9999))
            return rows

    def _handle_error(self, exc: Exception, show_dialog: bool = True, scheduled: bool = False) -> None:
        self.loading = False
        if self.progress_after_id is not None:
            self.root.after_cancel(self.progress_after_id)
            self.progress_after_id = None
        self._set_progress(0)
        self.status_var.set("更新失敗")
        message = str(exc)
        if "收盤資料" in message or "官方收盤資料" in message:
            self.fundamental_refresh_status_var.set(message)
        else:
            self.fundamental_refresh_status_var.set("收盤價：讀取失敗")
        if show_dialog:
            messagebox.showerror("更新失敗", str(exc))

    def _clear_cards(self) -> None:
        for frame in self.card_frames:
            frame.destroy()
        self.card_frames.clear()

    def _build_card(self, index: int, row: dict, mode: str) -> None:
        card_bg, border_color = rank_card_style(index)
        card = tk.Frame(self.card_container, bg=card_bg, highlightbackground=border_color, highlightthickness=2 if index < 3 else 1, bd=0)
        card.grid(row=0, column=index, sticky="nsew", padx=6, pady=6)
        self.card_container.grid_columnconfigure(index, weight=1)

        trend, trend_color = trend_text(row)
        match_count = row.get("hard_filter_match_count", 0) + row.get("condition_match_count", 0)
        quality_label = "精選" if row.get("hard_filter_pass") else "候補"
        quality_color = SELECTED_COLOR if quality_label == "精選" else FALLBACK_COLOR
        score = row.get("recommendation_score") or 0.0

        detail_text = tk.Text(card, height=10, wrap="word", font=("Microsoft JhengHei UI", 9), bg=card_bg, fg=TEXT_MID, relief="flat", bd=0)
        detail_text.pack(fill="both", expand=True, padx=12, pady=12)
        detail_text.tag_configure("rank", foreground=border_color, font=("Segoe UI Emoji", 13, "bold"))
        detail_text.tag_configure("name", foreground=TEXT_DARK, font=("Microsoft JhengHei UI", 10, "bold"))
        detail_text.tag_configure("trend", foreground=trend_color, font=("Segoe UI", 10, "bold"))
        detail_text.tag_configure("quality", foreground=quality_color, font=("Microsoft JhengHei UI", 9, "bold"))
        detail_text.insert("end", f"{rank_badge(index)}\n", "rank")
        detail_text.insert("end", f"{row['code']} {row['name']}\n", "name")
        detail_text.insert("end", f"股價 {row.get('price') or 0:.2f}  {trend}\n", "trend")
        detail_text.insert("end", f"{quality_label} | 推薦分數 {score:.2f} / 100\n", "quality")
        detail_text.insert("end", f"條件符合度 {match_count}/7\n")
        detail_text.insert("end", f"3 月平均 YoY {row.get('avg_revenue_growth_3m') or 0:.2f}%\n")
        detail_text.insert("end", f"EPS 年增 {row.get('eps_growth') or 0:.2f}%\n")
        detail_text.insert("end", f"ROE {row.get('roe') or 0:.2f}%\n")
        detail_text.insert("end", f"20 日漲幅 {row.get('pct_change_20d') or 0:.2f}%\n\n")
        detail_text.insert("end", "條件明細\n")
        for label, passed in build_condition_rows(row):
            detail_text.insert("end", f"{'✓' if passed else '✗'} {label}\n")
        detail_text.bind("<Key>", self._readonly_text)
        self.card_frames.append(card)

    def _render_dashboard(self) -> None:
        rows = self.dashboard.get("top_stocks", [])[:5]
        mode = self.dashboard.get("display_mode", "passed")
        if not rows and mode == "passed":
            rows = self.dashboard.get("passed_stocks", [])[:5]
        if not rows and mode != "passed":
            rows = self.dashboard.get("fallback_stocks", [])[:5]

        if mode == "passed":
            self.mode_var.set("目前顯示：總條件數優先排名，前段皆為精選")
        elif mode == "mixed":
            self.mode_var.set("目前顯示：總條件數優先排名，含精選與觀察股")
        else:
            self.mode_var.set("目前顯示：總條件數優先排名")
        self._clear_cards()
        for row_id in self.tree.get_children():
            self.tree.delete(row_id)

        if not rows:
            self._set_summary("目前沒有可顯示的推薦結果。", [])
            self.tree.insert("", tk.END, values=("", "", "目前沒有資料", "", "", "", "", "", "", "", ""))
            return

        summary_items = []
        for index, row in enumerate(rows):
            self._build_card(index, row, mode)
            trend, color = trend_text(row)
            tag = "flat"
            if color == UP_COLOR:
                tag = "up"
            elif color == DOWN_COLOR:
                tag = "down"
            match_count = row.get("hard_filter_match_count", 0) + row.get("condition_match_count", 0)
            rank_tag = "rank_gold" if index == 0 else "rank_silver" if index == 1 else "rank_bronze" if index == 2 else None
            row_tags = (tag, rank_tag) if rank_tag else (tag,)
            self.tree.insert(
                "",
                tk.END,
                values=(
                    rank_badge(index),
                    row["code"],
                    row["name"],
                    f"{row.get('price') or 0:.2f}",
                    trend,
                    f"{(row.get('recommendation_score') or 0):.2f}/100",
                    f"{match_count}/7",
                    f"{row.get('eps_growth') or 0:.2f}",
                    f"{row.get('avg_revenue_growth_3m') or 0:.2f}",
                    f"{row.get('roe') or 0:.2f}",
                    f"{row.get('pct_change_20d') or 0:.2f}",
                ),
                tags=row_tags,
            )

            news = fallback_business_summary(row)
            quality_label = "精選" if row.get("hard_filter_pass") else "候補"
            summary_items.append(
                {
                    "text": (
                        f"{rank_badge(index)} {quality_label} {row['code']} {row['name']}\n"
                        f"股價 {row.get('price') or 0:.2f}，推薦分數 {(row.get('recommendation_score') or 0):.2f}/100，ROE {row.get('roe') or 0:.2f}%\n"
                        f"摘要：{news['summary']}\n"
                    ),
                    "label": news.get("label", ""),
                    "url": news.get("url", ""),
                }
            )
        self._set_summary("", summary_items)

    def _render_watchlist_table(self) -> None:
        for row_id in self.watch_tree.get_children():
            self.watch_tree.delete(row_id)
        today_text = date.today().isoformat()
        stock_names = {item["code"]: item.get("name", item["code"]) for item in self.watchlist_data.get("stocks", [])}
        rows_by_code = {item["code"]: item for item in self.watch_rows}

        for item in self.watchlist_data.get("stocks", []):
            code = item.get("code")
            row = rows_by_code.get(code)
            if row:
                trend, color = trend_text(row)
                sell_level, _ = build_sell_reasons(row)
                if color == UP_COLOR:
                    tag = "up"
                elif color == DOWN_COLOR:
                    tag = "down"
                else:
                    tag = "flat"
                self.watch_tree.insert(
                    "",
                    tk.END,
                    iid=code,
                    values=(
                        code,
                        row.get("name") or stock_names.get(code, code),
                        f"{row.get('price') or 0:.2f}",
                        trend,
                        f"{row.get('previous_close') or 0:.2f}",
                        sell_level,
                        row.get("realtime_at") or today_text,
                    ),
                    tags=(tag,),
                )
            else:
                self.watch_tree.insert(
                    "",
                    tk.END,
                    iid=code,
                    values=(code, stock_names.get(code, code), "--", "--", "--", "--", "--"),
                    tags=("flat",),
                )

    def _update_watch_history_storage(self) -> None:
        today_text = date.today().isoformat()
        history = self.watchlist_data.setdefault("history", {})
        for row in self.watch_rows:
            code = row["code"]
            history.setdefault(code, {})
            history[code][today_text] = {
                "price": row.get("price"),
                "change_pct": row.get("price_change_pct"),
                "previous_close": row.get("previous_close"),
            }
        save_watchlist_data(self.watchlist_data)

    def _render_watch_history(self, code: str) -> None:
        self.watch_history_text.delete("1.0", "end")
        self.watch_sell_text.delete("1.0", "end")
        self.watch_sell_text.tag_configure("urgent", foreground=SELL_URGENT_COLOR, font=("Microsoft JhengHei UI", 11, "bold"))
        self.watch_sell_text.tag_configure("watch", foreground=SELL_WATCH_COLOR, font=("Microsoft JhengHei UI", 11, "bold"))
        self.watch_sell_text.tag_configure("ok", foreground=SELL_OK_COLOR, font=("Microsoft JhengHei UI", 11, "bold"))
        stock_name = next((item.get("name", code) for item in self.watchlist_data.get("stocks", []) if item.get("code") == code), code)
        history = (self.watchlist_data.get("history") or {}).get(code, {})
        current_row = next((item for item in self.watch_rows if item.get("code") == code), None)

        if current_row:
            level, reasons = build_sell_reasons(current_row)
            if level == "立即留意":
                self.watch_sell_text.insert("1.0", f"{code} {stock_name}\n\n")
                self.watch_sell_text.insert("end", "等級：立即留意\n", "urgent")
                self.watch_sell_text.insert("end", "建議：已有較明確轉弱或失控訊號，建議優先檢查部位與停利停損。\n\n")
                for index, reason in enumerate(reasons, start=1):
                    self.watch_sell_text.insert("end", f"{index}. {reason}\n")
            elif level == "偏弱觀察":
                self.watch_sell_text.insert("1.0", f"{code} {stock_name}\n\n")
                self.watch_sell_text.insert("end", "等級：偏弱觀察\n", "watch")
                self.watch_sell_text.insert("end", "建議：目前已有偏弱跡象，建議持續觀察後續價格與基本面變化。\n\n")
                for index, reason in enumerate(reasons, start=1):
                    self.watch_sell_text.insert("end", f"{index}. {reason}\n")
            else:
                self.watch_sell_text.insert("1.0", f"{code} {stock_name}\n\n")
                self.watch_sell_text.insert("end", "等級：暫無訊號\n", "ok")
                self.watch_sell_text.insert("end", "建議：目前尚未觸發明確賣出訊號，暫時偏向續抱觀察。")
        else:
            self.watch_sell_text.insert("1.0", f"{code} {stock_name}\n\n目前尚未抓到最新資料，暫時無法判斷賣出建議。")

        if not history:
            self.watch_history_text.insert("1.0", f"{code} {stock_name}\n\n目前還沒有每日追蹤紀錄。")
            return
        self.watch_history_text.insert("1.0", f"{code} {stock_name}\n\n")
        for day in sorted(history.keys(), reverse=True):
            item = history[day]
            price = item.get("price")
            change_pct = item.get("change_pct")
            previous_close = item.get("previous_close")
            price_text = "--" if price is None else f"{price:.2f}"
            prev_text = "--" if previous_close is None else f"{previous_close:.2f}"
            if change_pct is None:
                change_text = "--"
            elif change_pct > 0:
                change_text = f"▲ {change_pct:.2f}%"
            elif change_pct < 0:
                change_text = f"▼ {abs(change_pct):.2f}%"
            else:
                change_text = "0.00%"
            self.watch_history_text.insert("end", f"{day}\n股價 {price_text} | 昨收 {prev_text} | 漲跌幅 {change_text}\n\n")

    def _on_watchlist_select(self, _event=None) -> None:
        selection = self.watch_tree.selection()
        if not selection:
            return
        self._render_watch_history(selection[0])

    def _set_dashboard(self, dashboard, watch_rows, latest_close_date="", quote_updated=0, quote_failed=0, market_index=None, quote_date="", from_cache: bool = False) -> None:
        self.loading = False
        if self.progress_after_id is not None:
            self.root.after_cancel(self.progress_after_id)
            self.progress_after_id = None
        self._set_progress(100)
        self.dashboard = dashboard
        self.watch_rows = watch_rows
        self.gui_snapshot = build_gui_snapshot_payload(
            dashboard,
            watch_rows,
            latest_close_date,
            quote_updated,
            quote_failed,
            market_index,
            quote_date,
            self.analysis_payload,
            self.podcast_meta,
            self.podcast_rows,
        )
        try:
            GUI_SNAPSHOT_PATH.write_text(json.dumps(self.gui_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        self._export_mobile_snapshot()
        self._update_watch_history_storage()

        snapshot_date = dashboard.get("snapshot_date", "")
        analyzed = dashboard.get("analyzed_count", 0)
        failed = dashboard.get("failed_count", 0)
        price_date = quote_date or latest_close_date or snapshot_date
        date_label = "今日股價" if quote_date else "收盤資料"
        self.status_var.set(f"{date_label} {display_date(price_date)}，分析成功 {analyzed} 檔，分析失敗 {failed} 檔")
        self.fundamental_refresh_status_var.set(format_close_status(price_date))
        if market_index and market_index.get("price") is not None:
            index_time = market_index.get("time") or datetime.now().strftime("%H:%M:%S")
            self.market_index_var.set(f"台股大盤指數 {market_index['price']:,.2f}")
            change = market_index.get("change")
            if change is None:
                market_color = TEXT_DARK
            elif change > 0:
                market_color = UP_COLOR
            elif change < 0:
                market_color = DOWN_COLOR
            else:
                market_color = TEXT_DARK
            self.market_index_label.configure(fg=market_color)
            self.market_index_detail_var.set(f"今日價格更新時間 {index_time}，畫面與自選股讀價成功 {quote_updated} 筆，失敗 {quote_failed} 筆")
        else:
            self.market_index_var.set(f"最新收盤資料 {display_date(price_date)}")
            self.market_index_label.configure(fg=TEXT_DARK)
            self.market_index_detail_var.set(f"畫面與自選股讀價成功 {quote_updated} 筆，失敗 {quote_failed} 筆")
        if self.watchlist_data.get("stocks"):
            self.watch_status_var.set(f"已更新 {len(self.watch_rows)} 檔自選股，會持續保留直到你刪除。")
        else:
            self.watch_status_var.set("目前沒有自選股，輸入代號後即可開始每日追蹤。")

        self._render_dashboard()
        self._render_watchlist_table()
        if self.auto_refresh_var.get():
            self._schedule_auto_refresh(immediate=True)

    def _ensure_candidate_map(self):
        if self.candidate_map:
            return
        with requests.Session() as session:
            session.headers.update({"User-Agent": USER_AGENT})
            self._load_gui_universe(session)

    def add_watchlist_stock(self) -> None:
        code = self.watch_input_var.get().strip()
        if not code:
            return
        if not code.isdigit():
            messagebox.showwarning("格式錯誤", "請輸入台股代號，例如 2330。")
            return
        self._ensure_candidate_map()
        candidate = self.candidate_map.get(code)
        if not candidate:
            messagebox.showwarning("查無代號", f"找不到代號 {code}，請確認是否為上市櫃股票。")
            return
        stocks = self.watchlist_data.setdefault("stocks", [])
        if any(item.get("code") == code for item in stocks):
            self.watch_status_var.set(f"{code} 已在自選股清單中。")
            self.watch_input_var.set("")
            return
        stocks.append({"code": code, "name": candidate.name})
        save_watchlist_data(self.watchlist_data)
        self.watch_input_var.set("")
        self.watch_status_var.set(f"已加入 {code} {candidate.name}，正在更新股價。")
        self.refresh_watchlist_async()

    def delete_watchlist_stock(self) -> None:
        selection = list(self.watch_tree.selection())
        code = selection[0] if selection else ""
        if not code:
            focus_id = self.watch_tree.focus()
            if focus_id:
                code = focus_id
        if not code:
            current = self.watch_tree.focus()
            if current:
                values = self.watch_tree.item(current, "values")
                if values:
                    code = str(values[0]).strip()
        if not code:
            messagebox.showinfo("尚未選取", "請先在左側自選股清單選取要刪除的股票。")
            return

        before_count = len(self.watchlist_data.get("stocks", []))
        self.watchlist_data["stocks"] = [item for item in self.watchlist_data.get("stocks", []) if item.get("code") != code]
        self.watchlist_data.setdefault("history", {}).pop(code, None)
        self.watch_rows = [item for item in self.watch_rows if item.get("code") != code]
        after_count = len(self.watchlist_data.get("stocks", []))
        if after_count == before_count:
            messagebox.showwarning("刪除失敗", f"找不到自選股 {code}，請重新選取後再試一次。")
            return
        save_watchlist_data(self.watchlist_data)
        self._render_watchlist_table()
        self.watch_sell_text.delete("1.0", "end")
        self.watch_sell_text.insert("1.0", "已刪除選取的自選股。")
        self.watch_history_text.delete("1.0", "end")
        self.watch_history_text.insert("1.0", "已刪除選取的自選股。")
        self.watch_status_var.set(f"已刪除 {code}。")

    def refresh_watchlist_async(self) -> None:
        if self.loading:
            return
        self.loading = True
        self.status_var.set("正在更新自選股股價，請稍候...")
        self._set_progress(0)
        if self.progress_after_id is not None:
            self.root.after_cancel(self.progress_after_id)
        self._animate_progress()
        threading.Thread(target=self._watchlist_worker, daemon=True).start()

    def _watchlist_worker(self) -> None:
        try:
            rows = self._fetch_watchlist_rows([item.get("code") for item in self.watchlist_data.get("stocks", []) if item.get("code")])
            quote_updated, quote_failed, _market_index, quote_date = self._fetch_latest_quotes(None, rows)
        except Exception as exc:
            self.root.after(0, lambda: self._handle_error(exc))
            return
        self.root.after(0, lambda: self._set_watchlist_rows(rows, quote_updated, quote_failed, quote_date))

    def _set_watchlist_rows(self, rows, quote_updated: int = 0, quote_failed: int = 0, quote_date: str = "") -> None:
        self.loading = False
        if self.progress_after_id is not None:
            self.root.after_cancel(self.progress_after_id)
            self.progress_after_id = None
        self._set_progress(100)
        self.watch_rows = rows
        if self.dashboard:
            self.gui_snapshot = build_gui_snapshot_payload(
                self.dashboard,
                rows,
                quote_date,
                quote_updated,
                quote_failed,
                None,
                quote_date,
                self.analysis_payload,
                self.podcast_meta,
                self.podcast_rows,
            )
            try:
                GUI_SNAPSHOT_PATH.write_text(json.dumps(self.gui_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                pass
            self._export_mobile_snapshot()
        self._update_watch_history_storage()
        self._render_watchlist_table()
        if rows:
            date_text = display_date(quote_date) if quote_date else "最新可用日期"
            self.watch_status_var.set(f"自選股已更新，共 {len(rows)} 檔；{date_text} 讀價成功 {quote_updated} 筆，失敗 {quote_failed} 筆。")
        else:
            self.watch_status_var.set("目前沒有可更新的自選股。")


def main() -> None:
    root = tk.Tk()
    ScreenerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
