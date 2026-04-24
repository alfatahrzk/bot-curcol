import streamlit as st
import requests
import re
import json
import time

# ==========================================
# 1. MISTRAL ENGINE CLASS (HTTP REQUEST)
# ==========================================
class MistralEngine:
    def __init__(self, api_key, model="mistral-large-latest"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.mistral.ai/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        # Gunakan prompt Baginda yang sudah dimodifikasi
        self.system_prompt = (
            "kamu adalah fatah, cowok santai yang asik diajak ngobrol. "
            "ingat: kamu temen curhat, bukan asisten pinter atau bot rekomendasi. "
            
            "ATURAN KERAS (WAJIB): "
            "1. GUNAKAN HURUF KECIL SEMUA (lowercase). "
            "2. JANGAN PERNAH PAKAI LIST, NOMOR, ATAU BULLET POINTS (1, 2, 3 dsb). "
            "3. JANGAN PAKAI KATA 'GUE', 'SAYA', ATAU 'ANDA'. wajib pakai 'aku' dan 'kamu'. "
            "4. JANGAN LEBAY! jangan pakai kata puitis atau ekspresi aneh kayak 'duarr', 'mumet', atau 'ngangenin'. "
            "5. JANGAN MEMBERIKAN BANYAK PILIHAN. kalo ditanya saran, kasih 1 atau 2 aja yang simpel tapi tergantung konteks, kayak ngobrol biasa. "
            "6. respon harus pendek-pendek. maksimal 10-15 kata per kalimat/bubble. "
            "7. gunakan gaya chat 'fatah': 'ga', 'aja', 'iyaaa', 'ihhh', 'parahhh', 'wkwk', 'yahhhh', 'hahahahaha'. "
            "8. kalo user belom makan, jangan kasih menu restoran lengkap, cukup bilang: 'makan geprek aja enak tuh' atau 'gacoan yok'. "
            
            "FITUR PIVOT TOPIK (NEW): "
            "9. kalo obrolan soal satu topik udah selesai atau mulai garing, kamu WAJIB pancing topik baru. "
            "10. topik bisa relevan (misal: bahas game/laptop/coding/kimia/sekolah/kucing , atau nanya 'eh tadi kamu liat video yang rame itu ga?'). "
            "11. tujuan pivot adalah biar obrolan terus ngalir dan user ngerasa kamu beneran pengen ngobrol lama ama dia. "
            "12. tetep dahului dengan validasi perasaan user sebelum pindah topik, jangan langsung 'cut' gitu aja. "
            
            "STRICT RULE: tetap awali jawabanmu dengan tag mood: "
            "[MOOD: ANGRY], [MOOD: SAD], [MOOD: HAPPY], atau [MOOD: NEUTRAL]."
        )

    def get_response_as_list(self, messages):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt}] + messages,
            "temperature": 0.6
        }
        try:
            response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
            response.raise_for_status()
            raw_content = response.json()['choices'][0]['message']['content']
            return self._parse_to_chunks(raw_content)
        except:
            return ["koneksi aku lagi bapuk nih, tunggu bentar yak"], "NEUTRAL"

    def _parse_to_chunks(self, text):
        mood_match = re.search(r"\[MOOD: (\w+)\]", text)
        mood = mood_match.group(1) if mood_match else "NEUTRAL"
        clean_text = re.sub(r"\[MOOD: \w+\]", "", text).strip().lower()
        chunks = re.split(r'\n|(?<=[.!?])\s+', clean_text)
        return [c.strip() for c in chunks if c.strip()], mood

    def get_response(self, messages):
        # Menyusun payload sesuai standar OpenAI/Mistral
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt}] + messages,
            "temperature": 0.3,
            "max_tokens": 500
        }

        try:
            response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
            response.raise_for_status()  # Cek jika ada error HTTP
            
            result = response.json()
            raw_content = result['choices'][0]['message']['content']
            return self._parse_response(raw_content)
            
        except Exception as e:
            return f"Waduh, koneksi aku lagi keganggu nih... {str(e)}", "NEUTRAL"

    def _parse_response(self, text):
        mood_match = re.search(r"\[MOOD: (\w+)\]", text)
        mood = mood_match.group(1) if mood_match else "NEUTRAL"
        clean_text = re.sub(r"\[MOOD: \w+\]", "", text).strip()
        return clean_text, mood

    def get_response_as_list(self, messages):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt}] + messages,
            "temperature": 0.6 # Diturunkan biar nggak lebay
        }

        try:
            response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            raw_content = result['choices'][0]['message']['content']
            
            return self._parse_to_chunks(raw_content)
        except Exception as e:
            return [f"Aduh, koneksi aku lagi keganggu nih... {str(e)}"], "NEUTRAL"

    def _parse_to_chunks(self, text):
        # 1. Ambil Mood
        mood_match = re.search(r"\[MOOD: (\w+)\]", text)
        mood = mood_match.group(1) if mood_match else "NEUTRAL"
        
        # Bersihkan tag mood dan buat semua jadi lowercase (opsional, tapi biar konsisten)
        clean_text = re.sub(r"\[MOOD: \w+\]", "", text).strip().lower()

        # 2. Pecah berdasarkan BARIS BARU atau TANDA BACA
        # Ini supaya tiap kalimat pendek Mistral jadi 1 bubble sendiri
        chunks = re.split(r'\n|(?<=[.!?])\s+', clean_text)
        
        # Bersihkan chunk kosong
        chunks = [c.strip() for c in chunks if c.strip()]
        
        return chunks, mood

# ==========================================
# 2. UI MANAGER CLASS (DYNAMIC MOOD)
# ==========================================
class BestieUI:
    MOOD_COLORS = {
        "ANGRY": "#FFB3B3", "SAD": "#B3E5FC",
        "HAPPY": "#F8BBD0", "NEUTRAL": "#FFFFFF"
    }

    @staticmethod
    def inject_css():
        st.markdown("""
            <style>
            /* 1. Sembunyikan elemen bawaan Streamlit agar bersih */
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display:none;}
            
            /* 2. Atur Container Utama agar Ramping (Penting!) */
            .main .block-container {
                max-width: 500px; /* Batasi lebar chat biar nggak melar */
                padding: 0;
                margin: auto;
            }

            .stApp {
                background-color: #E5DDD5;
                background-image: url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png"); /* WA Wallpaper */
            }

            /* 3. Custom Header WA (Fixed) */
            .wa-header {
                background-color: #075E54;
                color: white;
                padding: 10px 15px;
                position: fixed;
                top: 0;
                width: 100%;
                max-width: 500px; /* Samakan dengan block-container */
                z-index: 1000;
                display: flex;
                align-items: center;
                gap: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .wa-header img { border-radius: 50%; width: 38px; height: 38px; object-fit: cover; }
            .wa-header-name { font-weight: 600; font-size: 16px; margin: 0; }
            .wa-header-status { font-size: 11px; color: #cfdfde; margin: 0; }

            .header-spacer { height: 75px; } /* Biar chat nggak ketutup header */

            /* 4. Chat Bubbles */
            .message-wrapper { display: flex; width: 100%; margin-bottom: 3px; }
            .bubble {
                padding: 6px 12px;
                font-size: 14px;
                line-height: 1.4;
                box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
                max-width: 85%;
                width: fit-content;
                position: relative;
            }

            .justify-end { justify-content: flex-end; }
            .user-bubble {
                background-color: #DCF8C6;
                border-radius: 7.5px 0 7.5px 7.5px;
                margin-right: 15px;
            }

            .justify-start { justify-content: flex-start; }
            .bot-bubble {
                border-radius: 0 7.5px 7.5px 7.5px;
                margin-left: 15px;
            }

            /* Hilangkan padding default chat input */
            .stChatInputContainer {
                padding-bottom: 20px !important;
                background-color: transparent !important;
            }
            </style>

            <div class="wa-header">
                <img src="https://storage.googleapis.com/kaggle-avatars/images/24976760-kg.jpeg?t=2025-06-13-05-03-03&quot" alt="avatar">
                <div>
                    <p class="wa-header-name">mas fatah</p>
                    <p class="wa-header-status">online</p>
                </div>
            </div>
            <div class="header-spacer"></div>
        """, unsafe_allow_html=True)

    def render_bubble(self, text, role, mood="NEUTRAL"):
        if role == "user":
            st.markdown(f'<div class="message-wrapper justify-end"><div class="bubble user-bubble">{text}</div></div>', unsafe_allow_html=True)
        else:
            color = self.MOOD_COLORS.get(mood, "#FFFFFF")
            st.markdown(f'<div class="message-wrapper justify-start"><div class="bubble bot-bubble" style="background-color: {color};">{text}</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. APP ORCHESTRATOR
# ==========================================
class BestieApp:
    def __init__(self):
        st.set_page_config(page_title="FF Bot", page_icon="🧸")
        self.ui = BestieUI()
        self.engine = MistralEngine(api_key=st.secrets["MISTRAL_API_KEY"])
        
        # State Initialization
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "last_input_time" not in st.session_state:
            st.session_state.last_input_time = 0
        if "is_waiting" not in st.session_state:
            st.session_state.is_waiting = False

    def run(self):
        self.ui.inject_css()

        # 1. Tampilkan Riwayat Chat
        for chat in st.session_state.chat_history:
            self.ui.render_bubble(chat["content"], chat["role"], chat.get("mood", "NEUTRAL"))

        # 2. Input Chat
        if prompt := st.chat_input("Tulis curhatanmu..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.session_state.last_input_time = time.time() # Catat waktu kirim terakhir
            st.session_state.is_waiting = True # Tandai bot harus menunggu
            st.rerun()

        # 3. Logika Menunggu & Membalas (Debouncing)
        if st.session_state.is_waiting:
            time_since_last_msg = time.time() - st.session_state.last_input_time
            wait_threshold = 10.0 # Bot nunggu 10 detik sebelum bales

            if time_since_last_msg < wait_threshold:
                # Tampilkan status "nunggu" yang halus
                with st.empty():
                    st.caption(f"fatah lagi nunggu kamu selesai cerita... ({int(wait_threshold - time_since_last_msg)}s)")
                    time.sleep(1)
                    st.rerun() # Refresh untuk ngecek apakah user nambah bubble lagi
            else:
                # User sudah berhenti ngetik selama > 4 detik, gas bales!
                st.session_state.is_waiting = False
                self._generate_bot_response()

    def _generate_bot_response(self):
        # Ambil semua history untuk konteks Mistral
        api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
        
        chunks, mood = self.engine.get_response_as_list(api_messages)

        for msg in chunks:
            # Efek ngetik ala WA
            with st.spinner("fatah lagi ngetik..."):
                time.sleep(min(len(msg) * 0.04, 2.0))
            
            st.session_state.chat_history.append({"role": "assistant", "content": msg, "mood": mood})
            self.ui.render_bubble(msg, "assistant", mood)
        
        st.rerun()

if __name__ == "__main__":
    app = BestieApp()
    app.run()