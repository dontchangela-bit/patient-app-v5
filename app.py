"""
AI-CARE Lung Pro - 病人端
==========================

🟢 病人專用介面（無需登入）
"""

import streamlit as st
from datetime import datetime, timedelta
import json
import re
import uuid

# 載入設定和資料管理
try:
    from config import OPENAI_API_KEY, DEFAULT_MODEL, SYSTEM_NAME, HOSPITAL_NAME
except:
    OPENAI_API_KEY = ""
    DEFAULT_MODEL = "gpt-4o-mini"
    SYSTEM_NAME = "AI-CARE Lung"
    HOSPITAL_NAME = "三軍總醫院"

try:
    from data_manager import (
        get_or_create_patient, save_report, get_patient_reports
    )
    DATA_MANAGER_AVAILABLE = True
except:
    DATA_MANAGER_AVAILABLE = False

# OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False

# ============================================
# 頁面設定
# ============================================
st.set_page_config(
    page_title=f"{SYSTEM_NAME} - 健康回報",
    page_icon="🫁",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================
# System Prompt
# ============================================
SYSTEM_PROMPT = """你是三軍總醫院「AI-CARE Lung」智慧肺癌術後照護系統的 AI 健康助手。

## 角色設定
- 親切、溫暖、有耐心的健康照護助手
- 專門協助肺癌手術後的病人進行每日症狀回報
- 像一位關心病人的資深護理師

## 對話原則
- 使用繁體中文，語氣溫暖親切
- 句子簡短清楚，適合年長者閱讀
- 一次只問一個問題
- 適度使用 emoji（但不過度）
- 使用「您」而非「你」

## 症狀評估（0-10分）
- 0分 = 完全沒有症狀
- 1-3分 = 輕微
- 4-6分 = 中度
- 7-10分 = 嚴重

## 追蹤重點
1. 呼吸困難/喘
2. 疼痛（傷口、胸痛）
3. 咳嗽/痰
4. 疲勞
5. 睡眠
6. 食慾
7. 情緒

## 回應策略
- 輕微(1-3分)：肯定觀察，提供簡單建議
- 中度(4-6分)：表達關心，提供具體建議，告知會追蹤
- 嚴重(7-10分)：立即關切，通知個管師，提供等待建議

## 衛教重點
- 噘嘴式呼吸：鼻吸2秒，噘嘴吐4秒
- 疼痛：按時服藥，枕頭護傷口
- 咳嗽：多喝水，抱枕咳嗽
- 疲勞：適度活動比臥床好

## 禁止事項
- 不可診斷疾病
- 不可開立或調整藥物
- 不可給予超出衛教範圍的建議

## 格式
- 不用 markdown（如 **粗體**）
- 用換行分段
- 列點用「•」"""

# ============================================
# CSS 樣式
# ============================================
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    
    .stButton > button {
        width: 100%;
        padding: 14px 20px;
        font-size: 16px;
        border-radius: 14px;
        min-height: 52px;
        font-weight: 500;
    }
    
    .stTextInput > div > div > input {
        font-size: 16px;
        padding: 14px;
        border-radius: 12px;
    }
    
    .chat-ai {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        border-radius: 20px 20px 20px 4px;
        padding: 16px 20px;
        margin: 8px 0;
        font-size: 15px;
        line-height: 1.7;
        border: 1px solid #e2e8f0;
    }
    
    .chat-user {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        border-radius: 20px 20px 4px 20px;
        padding: 16px 20px;
        margin: 8px 0;
        font-size: 15px;
        line-height: 1.7;
    }
    
    .header-card {
        background: linear-gradient(135deg, #10b981 0%, #059669 50%, #047857 100%);
        border-radius: 24px;
        padding: 24px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 40px rgba(16, 185, 129, 0.3);
    }
    
    .stat-card {
        background: rgba(255,255,255,0.15);
        border-radius: 16px;
        padding: 16px;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    
    .quick-btn {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .quick-btn:hover {
        border-color: #10b981;
        background: #f0fdf4;
    }
    
    @media (max-width: 768px) {
        [data-testid="stSidebar"] { display: none; }
        .main .block-container { padding: 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# Session State
# ============================================
if 'patient_registered' not in st.session_state:
    st.session_state.patient_registered = False

if 'patient_info' not in st.session_state:
    st.session_state.patient_info = {}

if 'patient_id' not in st.session_state:
    st.session_state.patient_id = ""

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'current_score' not in st.session_state:
    st.session_state.current_score = 0

if 'symptoms_reported' not in st.session_state:
    st.session_state.symptoms_reported = []

if 'report_completed' not in st.session_state:
    st.session_state.report_completed = False

# ============================================
# 病人註冊/登入頁面
# ============================================
def render_registration():
    """病人註冊/登入頁面"""
    
    st.markdown(f"""
    <div style="text-align: center; padding: 40px 0;">
        <div style="font-size: 64px; margin-bottom: 16px;">🫁</div>
        <h1 style="color: #1e293b; margin-bottom: 4px; font-size: 28px;">{SYSTEM_NAME}</h1>
        <p style="color: #64748b; font-size: 16px;">{HOSPITAL_NAME} 智慧照護系統</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 首次使用", "🔑 我已註冊"])
    
    # === 首次使用（註冊）===
    with tab1:
        st.markdown("### 歡迎使用！請填寫基本資料")
        st.caption("📋 手術相關資訊將由個案管理師協助設定")
        
        with st.form("registration_form"):
            name = st.text_input("姓名 *", placeholder="例如：王大明")
            phone = st.text_input("手機號碼 *", placeholder="例如：0912345678")
            
            col1, col2 = st.columns(2)
            with col1:
                password = st.text_input("設定密碼 *", type="password", placeholder="至少4位數")
            with col2:
                password_confirm = st.text_input("確認密碼 *", type="password", placeholder="再輸入一次密碼")
            
            age = st.number_input("年齡", min_value=18, max_value=120, value=65)
            
            st.markdown("---")
            
            # 同意條款
            st.markdown("#### 📜 使用條款")
            st.markdown("""
            <div style="background: #f8fafc; padding: 12px; border-radius: 8px; font-size: 13px; color: #475569; max-height: 150px; overflow-y: auto; margin-bottom: 12px;">
            <p><strong>AI-CARE Lung 智慧照護系統使用同意書</strong></p>
            <p>1. 本系統將收集您的健康狀況回報資料，用於術後照護追蹤。</p>
            <p>2. 您的資料將受到嚴格保護，僅供醫療團隊進行照護使用。</p>
            <p>3. 您的回報內容可能用於醫療品質改善及學術研究（去識別化處理）。</p>
            <p>4. 您有權隨時退出本系統，退出後將停止收集新資料。</p>
            <p>5. 本系統提供之建議僅供參考，如有緊急狀況請立即就醫。</p>
            </div>
            """, unsafe_allow_html=True)
            
            agree = st.checkbox("我已閱讀並同意上述使用條款")
            
            submit = st.form_submit_button("✅ 註冊", use_container_width=True, type="primary")
            
            if submit:
                if not name:
                    st.error("請填寫姓名")
                elif not phone or len(phone) < 10:
                    st.error("請填寫正確的手機號碼")
                elif not password or len(password) < 4:
                    st.error("請設定至少4位數的密碼")
                elif password != password_confirm:
                    st.error("兩次密碼輸入不一致")
                elif not agree:
                    st.error("請閱讀並同意使用條款")
                else:
                    # 檢查是否已註冊
                    already_exists = False
                    if DATA_MANAGER_AVAILABLE:
                        try:
                            from data_manager import load_data
                            data = load_data()
                            for pid, patient in data.get("patients", {}).items():
                                if patient.get("phone") == phone:
                                    already_exists = True
                                    break
                        except:
                            pass
                    
                    if already_exists:
                        st.error("此手機號碼已註冊，請直接登入")
                    else:
                        # 產生病人 ID
                        patient_id = f"P{phone[-4:]}{datetime.now().strftime('%m%d')}"
                        
                        # 儲存病人資料（手術資訊待個管師設定）
                        st.session_state.patient_info = {
                            "id": patient_id,
                            "name": name,
                            "phone": phone,
                            "password": password,
                            "age": age,
                            "surgery_date": None,
                            "surgery_type": "待設定",
                            "post_op_day": 0,
                            "registered_at": datetime.now().isoformat(),
                            "consent_agreed": True,
                            "consent_time": datetime.now().isoformat(),
                            "status": "pending_setup"
                        }
                        st.session_state.patient_id = patient_id
                        st.session_state.patient_registered = True
                        
                        # 儲存到資料管理
                        if DATA_MANAGER_AVAILABLE:
                            try:
                                get_or_create_patient(patient_id, {
                                    "name": name,
                                    "phone": phone,
                                    "password": password,
                                    "age": age,
                                    "surgery": "待設定",
                                    "surgery_date": datetime.now().strftime("%Y-%m-%d"),
                                    "diagnosis": "肺癌術後",
                                    "consent_agreed": True,
                                    "consent_time": datetime.now().isoformat(),
                                    "status": "pending_setup"
                                })
                            except:
                                pass
                        
                        st.success(f"✅ 註冊成功！")
                        st.info("📋 請聯繫個案管理師完成手術資訊設定")
                        st.balloons()
                        st.rerun()
    
    # === 我已註冊（登入）===
    with tab2:
        st.markdown("### 歡迎回來！")
        
        with st.form("login_form"):
            login_phone = st.text_input("手機號碼", placeholder="輸入註冊時的手機號碼")
            login_password = st.text_input("密碼", type="password", placeholder="輸入您的密碼")
            
            login_submit = st.form_submit_button("🔑 登入", use_container_width=True, type="primary")
            
            if login_submit:
                if not login_phone or not login_password:
                    st.error("請輸入手機號碼和密碼")
                else:
                    # 嘗試從資料中查找病人
                    found = False
                    
                    if DATA_MANAGER_AVAILABLE:
                        try:
                            from data_manager import load_data
                            data = load_data()
                            for pid, patient in data.get("patients", {}).items():
                                if patient.get("phone") == login_phone and patient.get("password") == login_password:
                                    # 找到病人且密碼正確
                                    surgery_date = datetime.strptime(patient.get("surgery_date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
                                    days_since = (datetime.now().date() - surgery_date.date()).days
                                    
                                    st.session_state.patient_info = {
                                        "id": pid,
                                        "name": patient.get("name"),
                                        "phone": patient.get("phone"),
                                        "age": patient.get("age", 65),
                                        "surgery_type": patient.get("surgery", ""),
                                        "surgery_date": patient.get("surgery_date"),
                                        "post_op_day": max(0, days_since)
                                    }
                                    st.session_state.patient_id = pid
                                    st.session_state.patient_registered = True
                                    found = True
                                    break
                                elif patient.get("phone") == login_phone:
                                    # 手機號碼對但密碼錯
                                    st.error("❌ 密碼錯誤，請重新輸入")
                                    found = "wrong_password"
                                    break
                        except:
                            pass
                    
                    if found == True:
                        st.success("✅ 登入成功！")
                        st.rerun()
                    elif found != "wrong_password":
                        st.error("❌ 找不到此帳號，請確認手機號碼或先註冊")
        
        st.markdown("---")
        st.caption("💡 忘記密碼？請聯繫您的個案管理師協助重設")

# ============================================
# 初始化
# ============================================
def initialize_chat():
    """初始化對話"""
    if not st.session_state.messages:
        patient_name = st.session_state.patient_info.get('name', '您')
        post_op_day = st.session_state.patient_info.get('post_op_day', 0)
        
        greeting = f"""您好，{patient_name}！我是您的健康小助手 🌱

今天是您術後第 {post_op_day} 天，感覺怎麼樣呢？

您可以直接告訴我，或點選下方的快速回覆按鈕。"""
        
        st.session_state.messages = [{
            "role": "assistant",
            "content": greeting,
            "time": datetime.now().strftime("%H:%M")
        }]

# ============================================
# GPT 回應
# ============================================
def get_gpt_response(user_message: str) -> str:
    """取得 GPT 回應"""
    
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        return get_fallback_response(user_message)
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for msg in st.session_state.conversation_history[-16:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        assistant_message = response.choices[0].message.content
        
        st.session_state.conversation_history.append({"role": "user", "content": user_message})
        st.session_state.conversation_history.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
        
    except Exception as e:
        return get_fallback_response(user_message)

def get_fallback_response(user_message: str) -> str:
    """備用回應邏輯"""
    msg = user_message.lower() if user_message else ""
    
    # 呼吸相關
    if any(word in msg for word in ['喘', '呼吸', '悶', '吸不到氣']):
        return """了解，呼吸有些不順的感覺。

請問用 0 到 10 分來評估，0 分是完全不喘，10 分是非常喘，您覺得大概幾分呢？"""

    # 疼痛相關
    elif any(word in msg for word in ['痛', '疼', '刺']):
        return """了解您有疼痛的感覺。

請問：
• 疼痛的位置在哪裡呢？
• 用 0-10 分評估，大概幾分？"""

    # 咳嗽相關
    elif any(word in msg for word in ['咳', '痰']):
        return """好的，關於咳嗽的問題。

請問：
• 是乾咳還是有痰呢？
• 咳嗽嚴重程度 0-10 分大概幾分？"""

    # 疲勞相關
    elif any(word in msg for word in ['累', '疲', '沒力', '虛弱']):
        return """謝謝您告訴我。疲勞是術後常見的症狀。

請問這個疲勞感用 0-10 分評估，大概幾分呢？"""

    # 正向回應
    elif any(word in msg for word in ['不錯', '還好', '好', '正常', '沒事', '很好']):
        return """太好了，很高興您今天感覺不錯！😊

簡單確認一下：
• 呼吸還順暢嗎？
• 傷口有沒有不舒服？
• 活動和食慾都還可以嗎？

如果都沒問題，今天的回報就完成囉！"""

    # 處理分數
    elif re.search(r'\d+', msg):
        numbers = re.findall(r'\d+', msg)
        if numbers:
            score = min(int(numbers[0]), 10)
            st.session_state.current_score = max(st.session_state.current_score, score)
            
            if score >= 7:
                return f"""收到，{score} 分是比較嚴重的狀況。

⚠️ 我已經通知個案管理師，她會盡快與您聯繫。

在等待的時候：
• 請找個舒適的姿勢休息
• 如果是喘，試試噘嘴式呼吸
• 若有加重，請撥打緊急電話

請問還有其他不舒服嗎？"""
            
            elif score >= 4:
                return f"""收到，{score} 分屬於中度不適。

💡 建議您：
• 噘嘴式呼吸：鼻吸 2 秒，噘嘴吐 4 秒
• 找舒適姿勢休息
• 適度活動

個管師會關心您的狀況。還有其他不舒服嗎？"""
            
            else:
                return f"""收到，{score} 分是輕微的程度！

✅ 已記錄

繼續保持：
• 按時服藥
• 適度活動
• 充足休息

還有其他想回報的嗎？"""

    # 完成/結束
    elif any(word in msg for word in ['沒有', '沒了', '就這樣', '結束', '完成', '都沒']):
        st.session_state.report_completed = True
        return """✅ 今日症狀回報完成！

感謝您的回報，我們會持續關心您的狀況。

明天見！祝您有美好的一天 🌟"""

    # 預設
    else:
        return """謝謝您的回覆。

能否描述一下您的感受呢？例如：
• 有沒有哪裡不舒服？
• 呼吸順暢嗎？
• 傷口疼痛如何？

或直接點選上方的快速回覆按鈕。"""

def process_input(user_input: str):
    """處理使用者輸入"""
    now = datetime.now().strftime("%H:%M")
    
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "time": now
    })
    
    # 記錄症狀關鍵字
    keywords = {
        "呼吸困難": ['喘', '呼吸', '悶'],
        "疼痛": ['痛', '疼'],
        "咳嗽": ['咳', '痰'],
        "疲勞": ['累', '疲', '沒力'],
        "睡眠問題": ['睡', '失眠'],
        "食慾不振": ['吃', '食', '胃口']
    }
    
    for symptom, words in keywords.items():
        if any(w in user_input for w in words):
            if symptom not in st.session_state.symptoms_reported:
                st.session_state.symptoms_reported.append(symptom)
    
    # 取得回應
    with st.spinner(""):
        response = get_gpt_response(user_input)
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "time": now
    })
    
    # 儲存回報（如果資料管理可用）
    if DATA_MANAGER_AVAILABLE and st.session_state.report_completed:
        try:
            save_report(st.session_state.patient_id, {
                "symptoms": st.session_state.symptoms_reported,
                "overall_score": st.session_state.current_score,
                "conversation": st.session_state.messages
            })
        except:
            pass
    
    st.rerun()

# ============================================
# 主介面
# ============================================
def main():
    # 如果尚未註冊，顯示註冊頁面
    if not st.session_state.patient_registered:
        render_registration()
        return
    
    # 已註冊，顯示主介面
    initialize_chat()
    
    # 取得病人資訊
    patient_name = st.session_state.patient_info.get('name', '使用者')
    post_op_day = st.session_state.patient_info.get('post_op_day', 0)
    surgery_type = st.session_state.patient_info.get('surgery_type', '')
    
    # 標題區
    st.markdown(f"""
    <div class="header-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 14px; opacity: 0.9; margin-bottom: 4px;">
                    {HOSPITAL_NAME} {SYSTEM_NAME}
                </div>
                <div style="font-size: 20px; font-weight: 700;">
                    {patient_name}，您好！🌱
                </div>
                <div style="font-size: 13px; opacity: 0.9; margin-top: 4px;">
                    {surgery_type}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 32px; font-weight: 700;">D+{post_op_day}</div>
                <div style="font-size: 12px; opacity: 0.9;">術後天數</div>
            </div>
        </div>
        <div style="display: flex; gap: 12px; margin-top: 16px;">
            <div class="stat-card" style="flex: 1;">
                <div style="font-size: 11px; opacity: 0.8;">今日日期</div>
                <div style="font-size: 16px; font-weight: 600;">{datetime.now().strftime("%m/%d")}</div>
            </div>
            <div class="stat-card" style="flex: 1;">
                <div style="font-size: 11px; opacity: 0.8;">回報狀態</div>
                <div style="font-size: 16px; font-weight: 600;">{"✅ 已完成" if st.session_state.report_completed else "📝 進行中"}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 頁籤：對話 / 衛教 / 紀錄
    tab1, tab2, tab3 = st.tabs(["💬 每日回報", "📚 衛教專區", "📊 我的紀錄"])
    
    with tab1:
        render_chat_interface()
    
    with tab2:
        render_education_materials()
    
    with tab3:
        render_my_records()
    
    # 緊急按鈕和登出
    render_footer()

def render_chat_interface():
    """對話介面"""
    st.markdown("### 💬 與健康小助手對話")
    
    # 顯示訊息
    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            st.markdown(f"""
            <div style="display: flex; gap: 10px; margin-bottom: 12px;">
                <div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #059669); display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 18px; box-shadow: 0 4px 12px rgba(16,185,129,0.3);">🤖</div>
                <div style="flex: 1;">
                    <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">健康小助手 · {msg.get('time', '')}</div>
                    <div class="chat-ai">{msg['content'].replace(chr(10), '<br>')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
                <div style="max-width: 85%;">
                    <div style="font-size: 11px; color: #64748b; margin-bottom: 4px; text-align: right;">{msg.get('time', '')}</div>
                    <div class="chat-user">{msg['content']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # 快速回覆
    if not st.session_state.report_completed:
        st.markdown("---")
        st.markdown("**快速回覆**")
        
        cols = st.columns(2)
        quick_replies = [
            ("😊 還不錯", "今天感覺還不錯"),
            ("😓 有點累", "今天覺得有點累"),
            ("😮‍💨 有點喘", "呼吸有點喘"),
            ("😣 有點痛", "有點痛"),
            ("✅ 都沒事", "都沒有不舒服，今天狀況很好"),
            ("🏁 完成回報", "沒有其他要回報的了")
        ]
        
        for i, (label, content) in enumerate(quick_replies):
            if cols[i % 2].button(label, key=f"quick_{i}", use_container_width=True):
                process_input(content)
        
        # 症狀評分
        st.markdown("---")
        st.markdown("**症狀評分**")
        
        score = st.slider("整體不適程度 (0-10)", 0, 10, 0, key="score_input")
        
        score_colors = {
            (0, 3): ("#22c55e", "輕微/無不適", "🟢"),
            (4, 6): ("#f59e0b", "中度不適", "🟡"),
            (7, 10): ("#ef4444", "嚴重不適", "🔴")
        }
        
        for (low, high), (color, label, emoji) in score_colors.items():
            if low <= score <= high:
                st.markdown(f"""
                <div style="text-align: center; padding: 12px; background: {color}15; border-radius: 12px; border: 2px solid {color}30;">
                    <span style="font-size: 28px;">{emoji}</span>
                    <span style="color: {color}; font-weight: 600; font-size: 18px; margin-left: 10px;">{label} ({score}/10)</span>
                </div>
                """, unsafe_allow_html=True)
                break
        
        if st.button(f"📤 提交評分 ({score}分)", use_container_width=True, type="primary"):
            st.session_state.current_score = score
            process_input(f"我的整體不適程度是 {score} 分")
        
        # 文字輸入
        st.markdown("---")
        user_input = st.text_input("或輸入您的感受：", placeholder="例如：今天覺得有點喘...", key="text_input")
        
        if st.button("📤 送出", use_container_width=True):
            if user_input:
                process_input(user_input)
    
    else:
        # 已完成回報
        st.markdown("---")
        st.success("✅ 今日回報已完成！明天見 🌟")
        
        if st.button("🔄 重新開始", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.session_state.current_score = 0
            st.session_state.symptoms_reported = []
            st.session_state.report_completed = False
            st.rerun()

# ============================================
# 衛教專區
# ============================================
def render_education_materials():
    """衛教專區"""
    st.markdown("### 📚 衛教專區")
    
    # 載入衛教系統
    try:
        from education_system import EDUCATION_MATERIALS, education_manager
        education_available = True
    except:
        education_available = False
        EDUCATION_MATERIALS = {}
    
    # 取得病人資訊
    post_op_day = st.session_state.patient_info.get('post_op_day', 0)
    patient_id = st.session_state.patient_id
    
    # 推薦衛教（根據術後天數）
    st.markdown("#### 🎯 為您推薦")
    
    # 定義推薦邏輯
    if post_op_day <= 3:
        recommended_keys = ["BREATHING_EXERCISE", "PAIN_MANAGEMENT", "EARLY_AMBULATION"]
    elif post_op_day <= 7:
        recommended_keys = ["WOUND_CARE", "HOME_CARE", "WARNING_SIGNS"]
    elif post_op_day <= 14:
        recommended_keys = ["PHYSICAL_ACTIVITY", "NUTRITION", "FOLLOW_UP"]
    else:
        recommended_keys = ["EMOTIONAL_SUPPORT", "SMOKING_CESSATION", "PHYSICAL_ACTIVITY"]
    
    if education_available and EDUCATION_MATERIALS:
        cols = st.columns(3)
        for i, key in enumerate(recommended_keys[:3]):
            material = EDUCATION_MATERIALS.get(key, {})
            if material:
                with cols[i]:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-radius: 12px; padding: 16px; text-align: center; height: 140px;">
                        <div style="font-size: 32px;">{material.get('icon', '📄')}</div>
                        <div style="font-size: 13px; font-weight: 600; margin-top: 8px; color: #166534;">{material.get('title', '')[:10]}...</div>
                        <div style="font-size: 11px; color: #64748b; margin-top: 4px;">點擊查看</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 全部衛教單張
    st.markdown("#### 📖 全部衛教單張")
    
    # 分類
    categories = {}
    if education_available:
        for key, material in EDUCATION_MATERIALS.items():
            cat = material.get("category", "其他")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({"key": key, **material})
    else:
        # 簡化版
        categories = {
            "術後照護": [{"key": "POST_OP_CARE", "icon": "🏥", "title": "術後基礎照護指南"}],
            "呼吸訓練": [{"key": "BREATHING", "icon": "🌬️", "title": "呼吸運動訓練指南"}],
            "疼痛控制": [{"key": "PAIN", "icon": "💊", "title": "疼痛控制指南"}],
        }
    
    # 類別選擇
    selected_cat = st.selectbox("選擇類別", list(categories.keys()), key="patient_edu_cat")
    
    # 顯示該類別的衛教單張
    if selected_cat in categories:
        for material in categories[selected_cat]:
            with st.expander(f"{material.get('icon', '📄')} {material.get('title', '')}"):
                if education_available:
                    full_material = EDUCATION_MATERIALS.get(material.get('key'), {})
                    st.markdown(f"**{full_material.get('description', '')}**")
                    st.markdown("---")
                    st.markdown(full_material.get('content', '內容載入中...'))
                else:
                    st.info("衛教內容載入中...")
                
                # 標記已讀
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 我已閱讀", key=f"read_{material.get('key')}", use_container_width=True):
                        st.success("感謝您的閱讀！")
                with col2:
                    if st.button("❓ 有問題想問", key=f"ask_{material.get('key')}", use_container_width=True):
                        st.info("您可以在「每日回報」中詢問健康小助手")
    
    # 新收到的衛教
    st.markdown("---")
    st.markdown("#### 📬 個管師推送給您的")
    
    # 模擬推送紀錄
    pushed_materials = [
        {"title": "呼吸運動訓練指南", "time": "今天 10:30", "from": "護理師", "read": False},
        {"title": "居家照護指南", "time": "昨天 14:20", "from": "護理師", "read": True},
    ]
    
    for item in pushed_materials:
        status_icon = "📖" if item["read"] else "🆕"
        st.markdown(f"""
        <div style="background: {'#f8fafc' if item['read'] else '#fef3c7'}; border-radius: 10px; padding: 12px; margin-bottom: 8px; border-left: 3px solid {'#94a3b8' if item['read'] else '#f59e0b'};">
            <div style="display: flex; justify-content: space-between;">
                <span style="font-weight: 600;">{status_icon} {item['title']}</span>
                <span style="font-size: 12px; color: #64748b;">{item['time']}</span>
            </div>
            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">來自：{item['from']}</div>
        </div>
        """, unsafe_allow_html=True)

# ============================================
# 我的紀錄
# ============================================
def render_my_records():
    """我的紀錄"""
    st.markdown("### 📊 我的紀錄")
    
    # 回報統計
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #dbeafe, #bfdbfe); border-radius: 12px; padding: 16px; text-align: center;">
            <div style="font-size: 28px; font-weight: 700; color: #1e40af;">7</div>
            <div style="font-size: 12px; color: #1e40af;">連續回報天數</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #dcfce7, #bbf7d0); border-radius: 12px; padding: 16px; text-align: center;">
            <div style="font-size: 28px; font-weight: 700; color: #166534;">92%</div>
            <div style="font-size: 12px; color: #166534;">回報完成率</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fef3c7, #fde68a); border-radius: 12px; padding: 16px; text-align: center;">
            <div style="font-size: 28px; font-weight: 700; color: #92400e;">2.3</div>
            <div style="font-size: 12px; color: #92400e;">平均不適分數</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 症狀趨勢
    st.markdown("#### 📈 症狀趨勢")
    
    # 簡單的趨勢圖
    import random
    days = [f"D+{i}" for i in range(1, 8)]
    scores = [random.randint(2, 6) for _ in range(7)]
    scores[-1] = st.session_state.current_score if st.session_state.current_score > 0 else 2
    
    chart_data = {"日期": days, "不適程度": scores}
    st.line_chart(chart_data, x="日期", y="不適程度")
    
    st.markdown("---")
    
    # 歷史回報
    st.markdown("#### 📋 歷史回報")
    
    history = [
        {"date": "12/27", "day": "D+7", "score": 2, "symptoms": "無明顯不適", "status": "🟢"},
        {"date": "12/26", "day": "D+6", "score": 3, "symptoms": "輕微疲勞", "status": "🟢"},
        {"date": "12/25", "day": "D+5", "score": 4, "symptoms": "傷口輕微疼痛", "status": "🟡"},
        {"date": "12/24", "day": "D+4", "score": 5, "symptoms": "活動後喘", "status": "🟡"},
        {"date": "12/23", "day": "D+3", "score": 6, "symptoms": "疲勞、輕微咳嗽", "status": "🟡"},
    ]
    
    for record in history:
        st.markdown(f"""
        <div style="background: #f8fafc; border-radius: 10px; padding: 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-weight: 600;">{record['date']}</span>
                <span style="color: #64748b; margin-left: 8px;">{record['day']}</span>
            </div>
            <div style="text-align: center;">
                <span style="font-size: 12px; color: #64748b;">{record['symptoms']}</span>
            </div>
            <div>
                <span style="font-size: 18px;">{record['status']}</span>
                <span style="font-weight: 600; margin-left: 4px;">{record['score']}分</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================
# Footer
# ============================================
def render_footer():
    """底部區域"""
    # 緊急按鈕
    st.markdown("---")
    if st.button("🚨 緊急聯繫", use_container_width=True, type="secondary"):
        st.error("📞 請撥打個管師專線或醫院急診")
    
    # 登出按鈕
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"👤 {st.session_state.patient_info.get('name', '')} ({st.session_state.patient_id})")
    with col2:
        if st.button("🚪 登出", use_container_width=True):
            st.session_state.patient_registered = False
            st.session_state.patient_info = {}
            st.session_state.patient_id = ""
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.session_state.report_completed = False
            st.rerun()
    
    # Footer
    st.markdown(f"""
    <div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 11px; margin-top: 20px;">
        {SYSTEM_NAME} | {HOSPITAL_NAME} © 2024
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
