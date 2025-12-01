import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import base64
import plotly.graph_objects as go
from datetime import datetime
import uuid
from io import BytesIO
from PIL import Image

# --- 1. AYARLAR ---
st.set_page_config(page_title="PRO LİG ARENA", page_icon="⚽", layout="wide")
DATA_FILE = "halisaha_db_final.json"


# --- 2. VERİ YÖNETİMİ ---
def load_data():
    if not os.path.exists(DATA_FILE): return {"players": [], "matches": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"players": [], "matches": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


STATE = load_data()

# --- 3. MODERN TASARIM (GLASSMORPHISM) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@300;400;600&display=swap');

    /* GENEL ATMOSFER */
    .stApp {
        background-color: #0f172a;
        background-image: 
            radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4 { font-family: 'Rajdhani', sans-serif; text-transform: uppercase; letter-spacing: 1px; color: #fff !important; }

    /* MVP KARTI */
    .hero-card {
        background: linear-gradient(160deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95));
        border: 2px solid #ffd700;
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.15);
        text-align: center;
        padding: 20px;
        border-radius: 20px;
        position: relative;
        overflow: hidden;
    }
    .hero-avatar {
        width: 100px; height: 100px;
        border-radius: 50%; object-fit: cover;
        border: 3px solid #ffd700;
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.4);
        margin-bottom: 10px;
    }
    .hero-stat-box { background: rgba(255,255,255,0.05); padding: 5px 10px; border-radius: 8px; min-width: 60px; }

    /* LİSTELER */
    .list-row {
        display: flex; align-items: center;
        background: rgba(255,255,255,0.03); margin-bottom: 6px; padding: 8px 12px;
        border-radius: 10px; border-left: 3px solid rgba(255,255,255,0.1);
    }
    .rank-1 { border-left-color: #ffd700; background: linear-gradient(90deg, rgba(255,215,0,0.1), transparent); }
    .avatar-small { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-right: 10px; border: 1px solid rgba(255,255,255,0.2); }

    /* YÖNETİM KARTLARI */
    .admin-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 5px;
    }

    /* INPUT DÜZENLEME */
    .stTextInput input, .stNumberInput input, .stDateInput input { background-color: #1e293b !important; color: white !important; border: 1px solid #334155 !important; }
    .stButton>button { border-radius: 8px; font-weight: 600; transition: 0.3s; width: 100%; }

</style>
""", unsafe_allow_html=True)

# --- 4. HESAPLAMA MOTORU ---

WEIGHTS = {
    "Forvet": {"g": 0.60, "a": 0.30, "b": 0.10},
    "Orta Saha": {"g": 0.35, "a": 0.45, "b": 0.20},
    "Defans": {"g": 0.15, "a": 0.15, "b": 0.70},
    "Kaleci": {"g": 0.05, "a": 0.05, "b": 0.90}
}


def img_to_b64(file):
    try:
        img = Image.open(file);
        img.thumbnail((300, 300))
        buf = BytesIO();
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return None


def get_img(b64, default="https://cdn-icons-png.flaticon.com/512/166/166344.png"):
    return f"data:image/jpeg;base64,{b64}" if b64 else default


def calculate_stats():
    totals = {}
    for p in STATE['players']:
        totals[p['id']] = {
            'goals': 0, 'assists': 0, 'bonus': 0, 'matches': 0,
            'name': p['name'], 'id': p['id'], 'pos': p.get('position', 'Forvet'), 'photo': p.get('photo')
        }

    for m in STATE['matches']:
        for e in m['events']:
            pid = e['playerId']
            if pid in totals:
                totals[pid]['goals'] += e.get('goals', 0)
                totals[pid]['assists'] += e.get('assists', 0)
                totals[pid]['bonus'] += e.get('bonus', 0)
                if e.get('goals', 0) + e.get('assists', 0) + e.get('bonus', 0) > 0:
                    totals[pid]['matches'] += 1

    results = []
    for pid, d in totals.items():
        m = max(1, d['matches'])
        w = WEIGHTS.get(d['pos'], WEIGHTS["Forvet"])
        gpm, apm, bpm = d['goals'] / m, d['assists'] / m, d['bonus'] / m

        raw = (w['g'] * (1 - np.exp(-gpm * 1.2)) + w['a'] * (1 - np.exp(-apm * 1.2)) + w['b'] * (
                    1 - np.exp(-bpm * 1.5)))
        conf = 0.5 + 0.5 * min(1, d['matches'] / 4)
        rating = 4.0 + (6.0 * raw * conf)
        d['rating'] = round(min(10, max(4, rating)), 1)
        results.append(d)

    return pd.DataFrame(results)


def get_mvp(last_match):
    best_pid, best_score, best_stats = None, -1, {}
    for e in last_match['events']:
        s = (e.get('goals', 0) * 4) + (e.get('assists', 0) * 3) + (e.get('bonus', 0) * 5)
        if s > best_score:
            best_score, best_pid, best_stats = s, e['playerId'], e
    if best_pid:
        p = next((x for x in STATE['players'] if x['id'] == best_pid), None)
        return p, best_stats
    return None, None


# --- 5. RENDER FONKSİYONLARI ---

def render_list_html(df, col, label, color):
    if df.empty: return "<div style='color:#666;text-align:center'>Veri Yok</div>"
    df = df[df[col] > 0].sort_values(col, ascending=False).head(8)
    html = ""
    for idx, row in enumerate(df.itertuples()):
        rank_cls = f"rank-{idx + 1}" if idx < 3 else ""
        html += f"""
        <div class="list-row {rank_cls}">
            <div style="font-weight:900; width:20px; color:rgba(255,255,255,0.4)">{idx + 1}</div>
            <img src="{get_img(row.photo)}" class="avatar-small">
            <div style="flex-grow:1; font-weight:600; color:#eee; font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{row.name}</div>
            <div style="font-weight:800; font-size:15px; color:{color}">{int(getattr(row, col))}</div>
        </div>
        """
    return html


def radar_chart(p1, p2=None):
    cats = ['Bitiricilik', 'Oyun Kurma', 'Defans', 'Tecrübe']

    def get_vals(p):
        m = max(1, p['matches'])
        return [min(100, (p['goals'] / m) * 45), min(100, (p['assists'] / m) * 45), min(100, (p['bonus'] / m) * 60),
                min(100, m * 10)]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=get_vals(p1), theta=cats, fill='toself', name=p1['name'], line_color='#00d2ff'))

    # --- DÜZELTİLEN KISIM ---
    # Python, p2 bir DataFrame satırı olduğu için "if p2:" ifadesinde "Ambiguous" hatası veriyordu.
    # Bunu "if p2 is not None:" olarak değiştirdik.
    if p2 is not None:
        fig.add_trace(go.Scatterpolar(r=get_vals(p2), theta=cats, fill='toself', name=p2['name'], line_color='#ff0055'))
    # ------------------------

    fig.update_layout(polar=dict(
        radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor='rgba(255,255,255,0.1)'),
        bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)',
                      legend=dict(font=dict(color="white"), orientation="h", y=0), margin=dict(t=20, b=20, l=40, r=40))
    return fig


# --- 6. SAYFA YAPISI ---

st.markdown(
    "<h1 style='text-align:center; margin-bottom:10px; color:#fff; text-shadow: 0 0 20px rgba(59,130,246,0.6);'>PRO LEAGUE HUB</h1>",
    unsafe_allow_html=True)
menu = st.radio("", ["🏠 ARENA", "⚔️ ANALİZ", "📋 KADRO", "⚙️ YÖNETİM"], horizontal=True, label_visibility="collapsed")
df_stats = calculate_stats()

# --- 1. ARENA (DASHBOARD) ---
if menu == "🏠 ARENA":
    c_mvp, c_gol, c_asist = st.columns([1.2, 1, 1])

    with c_mvp:
        st.markdown("<h3 style='text-align:center; font-size:16px !important'>HAFTANIN YILDIZI</h3>",
                    unsafe_allow_html=True)
        if STATE['matches']:
            last_match = STATE['matches'][-1]
            mvp_p, mvp_s = get_mvp(last_match)
            if mvp_p:
                st.markdown(f"""
                <div class="hero-card">
                    <div style="color:#ffd700; font-size:12px; margin-bottom:5px; font-weight:800; letter-spacing:1px;">MVP • {last_match['date']}</div>
                    <img src="{get_img(mvp_p.get('photo'))}" class="hero-avatar">
                    <h2 style="margin:0; font-size:28px; color:white !important;">{mvp_p['name']}</h2>
                    <div style="color:#94a3b8; font-size:14px; margin-bottom:10px">{mvp_p['position']}</div>
                    <div style="display:flex; justify-content:center; gap:10px">
                        <div class="hero-stat-box"><div style="font-size:18px; font-weight:bold; color:#fff">{mvp_s.get('goals', 0)}</div><div style="font-size:9px; color:#aaa">GOL</div></div>
                        <div class="hero-stat-box"><div style="font-size:18px; font-weight:bold; color:#fff">{mvp_s.get('assists', 0)}</div><div style="font-size:9px; color:#aaa">AST</div></div>
                        <div class="hero-stat-box"><div style="font-size:18px; font-weight:bold; color:#fff">{mvp_s.get('bonus', 0)}</div><div style="font-size:9px; color:#aaa">DEF</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("MVP yok.")
        else:
            st.info("Maç Yok")

    with c_gol:
        st.markdown(
            "<h3 style='text-align:center; font-size:16px !important; color:#3b82f6 !important'>GOL KRALLIĞI</h3>",
            unsafe_allow_html=True)
        st.markdown(render_list_html(df_stats, 'goals', 'GOL', '#3b82f6'), unsafe_allow_html=True)

    with c_asist:
        st.markdown(
            "<h3 style='text-align:center; font-size:16px !important; color:#a855f7 !important'>ASİST KRALLIĞI</h3>",
            unsafe_allow_html=True)
        st.markdown(render_list_html(df_stats, 'assists', 'AST', '#a855f7'), unsafe_allow_html=True)

    st.write("");
    st.divider()
    with st.expander("📅 MAÇ GEÇMİŞİ"):
        if STATE['matches']:
            for m in reversed(STATE['matches']):
                sc = [
                    f"{next((p['name'] for p in STATE['players'] if p['id'] == e['playerId']), '?')} ({e.get('goals')})"
                    for e in m['events'] if e.get('goals', 0) > 0]
                st.caption(f"**{m['date']}** | {m.get('note', '-')} | ⚽ {', '.join(sc) if sc else 'Gol yok'}")
        else:
            st.write("Kayıt yok.")

# --- 2. ANALİZ (VS) ---
elif menu == "⚔️ ANALİZ":
    st.markdown("### ⚔️ OYUNCU KARŞILAŞTIRMA")
    if not df_stats.empty:
        names = df_stats['name'].tolist()
        if len(names) >= 2:
            c1, c2 = st.columns(2)
            p1_name = c1.selectbox("1. Oyuncu", names, index=0)
            p2_name = c2.selectbox("2. Oyuncu", names, index=1)

            p1_data = df_stats[df_stats['name'] == p1_name].iloc[0]
            p2_data = df_stats[df_stats['name'] == p2_name].iloc[0]

            col_L, col_M, col_R = st.columns([1, 2, 1])
            with col_L:
                st.markdown(
                    f"<div style='text-align:center'><img src='{get_img(p1_data['photo'])}' style='width:90px;height:90px;border-radius:50%;border:3px solid #00d2ff'><h1 style='color:#00d2ff !important; margin:0'>{p1_data['rating']}</h1><span style='font-size:12px;color:#aaa'>GENEL</span></div>",
                    unsafe_allow_html=True)
            with col_M:
                st.plotly_chart(radar_chart(p1_data, p2_data), use_container_width=True)
            with col_R:
                st.markdown(
                    f"<div style='text-align:center'><img src='{get_img(p2_data['photo'])}' style='width:90px;height:90px;border-radius:50%;border:3px solid #ff0055'><h1 style='color:#ff0055 !important; margin:0'>{p2_data['rating']}</h1><span style='font-size:12px;color:#aaa'>GENEL</span></div>",
                    unsafe_allow_html=True)

            st.markdown("#### DETAYLAR")
            comp_df = pd.DataFrame({
                'İstatistik': ['Oynadığı Maç', 'Gol', 'Asist', 'Defans Puanı'],
                p1_name: [p1_data['matches'], p1_data['goals'], p1_data['assists'], p1_data['bonus']],
                p2_name: [p2_data['matches'], p2_data['goals'], p2_data['assists'], p2_data['bonus']]
            }).set_index('İstatistik')
            st.table(comp_df)
        else:
            st.warning("Kıyaslama için en az 2 oyuncunun maça çıkmış olması gerekir.")
    else:
        st.info("Kıyaslama yapmak için önce oyuncu ekleyin ve maç verisi girin.")

# --- 3. KADRO ---
elif menu == "📋 KADRO":
    c_add, c_del = st.columns(2)
    with c_add:
        st.markdown("#### 👤 EKLE")
        with st.form("new_p"):
            n = st.text_input("Ad Soyad")
            p = st.selectbox("Mevki", ["Forvet", "Orta Saha", "Defans", "Kaleci"])
            f = st.file_uploader("Fotoğraf", type=['jpg', 'png'])
            if st.form_submit_button("KAYDET", type="primary"):
                STATE['players'].append(
                    {"id": str(uuid.uuid4()), "name": n, "num": 0, "position": p, "photo": img_to_b64(f)})
                save_data(STATE);
                st.success("Eklendi");
                st.rerun()

    with c_del:
        st.markdown("#### 🗑️ SİL")
        if STATE['players']:
            p_dict = {p['name']: p['id'] for p in STATE['players']}
            sel = st.selectbox("Oyuncu Seç", list(p_dict.keys()))
            if st.button("SİL", type="secondary"):
                STATE['players'] = [p for p in STATE['players'] if p['id'] != p_dict[sel]]
                save_data(STATE);
                st.warning("Silindi");
                st.rerun()

    st.divider();
    st.markdown("#### 🛡️ KADRO")
    if STATE['players']:
        cols = st.columns(5)
        for i, pl in enumerate(STATE['players']):
            with cols[i % 5]:
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.05);padding:10px;border-radius:12px;text-align:center;margin-bottom:10px'><img src='{get_img(pl.get('photo'))}' style='width:50px;height:50px;border-radius:50%;object-fit:cover;margin-bottom:5px'><div style='font-weight:bold;font-size:12px;color:#fff'>{pl['name']}</div><div style='font-size:10px;color:#aaa'>{pl['position']}</div></div>",
                    unsafe_allow_html=True)

# --- 4. YÖNETİM ---
elif menu == "⚙️ YÖNETİM":
    st.markdown("### 📝 TEKNİK PANEL")

    with st.container():
        st.markdown(
            "<div style='background:rgba(30,41,59,0.5); padding:20px; border-radius:15px; border:1px solid rgba(255,255,255,0.1);'>",
            unsafe_allow_html=True)
        with st.form("match_entry_v2"):
            d, n = st.columns(2);
            date = d.date_input("Tarih");
            note = n.text_input("Skor")
            st.divider();
            st.write("🔻 **PERFORMANS**")
            events = {}
            cols = st.columns(3)
            for i, p in enumerate(STATE['players']):
                with cols[i % 3]:
                    st.markdown(
                        f"<div class='admin-card'><div style='display:flex;align-items:center;margin-bottom:5px;'><img src='{get_img(p.get('photo'))}' style='width:24px;height:24px;border-radius:50%;margin-right:8px;'><b>{p['name']}</b></div></div>",
                        unsafe_allow_html=True)
                    cg, ca = st.columns(2)
                    g = cg.number_input("G", key=f"g{p['id']}", min_value=0)
                    a = ca.number_input("A", key=f"a{p['id']}", min_value=0)
                    b = 0
                    if p['position'] in ['Defans', 'Kaleci', 'Orta Saha']:
                        b = st.number_input("Bonus", key=f"b{p['id']}", min_value=0)
                    events[p['id']] = {'g': g, 'a': a, 'b': b}

            st.write("")
            if st.form_submit_button("MAÇI İŞLE", type="primary"):
                dat = [{"playerId": k, "goals": v['g'], "assists": v['a'], "bonus": v['b']} for k, v in events.items()
                       if v['g'] + v['a'] + v['b'] > 0]
                if dat: STATE['matches'].append(
                    {"id": str(uuid.uuid4()), "date": str(date), "note": note, "events": dat}); save_data(
                    STATE); st.balloons(); st.success("Kaydedildi"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if STATE['matches'] and st.button("↩️ SON MAÇI SİL", type="secondary"): STATE['matches'].pop(); save_data(
            STATE); st.rerun()
    with c2:
        with st.expander("☢️ SIFIRLAMA"):
            if st.button("TÜMÜNÜ SİL"): save_data({"players": [], "matches": []}); st.rerun()