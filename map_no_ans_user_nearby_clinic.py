# map_with_clinic_circles.py
import pandas as pd
import folium
from folium.plugins import MarkerCluster,  BeautifyIcon
from branca.element import Template, MacroElement

# === 讀檔 ===
tmp27 = pd.read_csv("solta_cqa_yes&no_ans_user.csv")  # 消費者，含 consultant 欄位
tmp24 = pd.read_csv("clinic_location.csv")  # 診所，含 lats-tgos, lons-tgos

# 地圖中心
center = [tmp27["LATITUDE"].mean(), tmp27["LONGITUDE"].mean()] if len(tmp27) else [23.7, 121]
m = folium.Map(location=center, zoom_start=7, control_scale=True)  # 顯示比例尺

# 三個圖層
fg_consumers = folium.FeatureGroup(name="消費者 (藍色)", show=True)
fg_consultY  = folium.FeatureGroup(name="顧問 Y (黃色)", show=True)
fg_clinics   = folium.FeatureGroup(name="診所 (紅色十字+誤差圈)", show=True)

# 兩個群聚：只給消費者與顧問Y
mc_consumers = MarkerCluster(name=None, control=False).add_to(fg_consumers)
mc_consultY  = MarkerCluster(name=None, control=False).add_to(fg_consultY)

# BeautifyIcon（黃色），失敗則退回 folium.Icon
try:
    from folium.plugins import BeautifyIcon
    use_beautify = True
except Exception:
    use_beautify = False

# === 診所（不聚合，附帶紅色圓圈）===
for _, r in tmp24.iterrows():
    lat_t, lon_t = r.get("lats-tgos"), r.get("lons-tgos")
    if pd.notna(lat_t) and pd.notna(lon_t):
        folium.Marker(
            [lat_t, lon_t],
            popup=folium.Popup(f"Clinic: {r.get('clinic','')}", max_width=300),
            icon=folium.Icon(color="red", icon="plus-sign", prefix="glyphicon")
        ).add_to(fg_clinics)

        # 紅色誤差圈（固定 50m，可改成讀取 max_error_range）
        folium.Circle(
            [lat_t, lon_t],
            radius=50,
            color="red",
            fill=True,
            fill_opacity=0.1
        ).add_to(fg_clinics)

# === 消費者與顧問Y ===
for _, r in tmp27.iterrows():
    lat, lon = r.get("LATITUDE"), r.get("LONGITUDE")
    if not (pd.notna(lat) and pd.notna(lon)):
        continue

    acc = float(r.get("ACCURACY", 0) or 0)
    is_Y = str(r.get("consultant","")).strip().upper() == "Y"
    popup_html = (
        f"診所: {r.get('CONSUMER_ANS','') or ''}<br>"
        f"IM_ID: {r.get('IM_ID','') or ''}<br>"
        f"AUTH_CODE: {r.get('Short_code','') or ''}"
    )
    popup = folium.Popup(popup_html, max_width=300)   # ✅ 指定寬度

    if is_Y:
        icon = (BeautifyIcon(icon="user", icon_shape="marker", text_color="#fff",
                             background_color="#FFD400", border_color="#C9A400")
                if use_beautify else folium.Icon(color="orange", icon="user", prefix="glyphicon"))
        folium.Marker([lat, lon], popup=popup, icon=icon).add_to(mc_consultY)
        if acc > 0:
            folium.Circle([lat, lon], radius=acc, color="#FFD400",
                          fill=True, fill_opacity=0.10).add_to(fg_consultY)
    else:
        icon = folium.Icon(color="blue", icon="user", prefix="glyphicon")
        folium.Marker([lat, lon], popup=popup, icon=icon).add_to(mc_consumers)
        if acc > 0:
            folium.Circle([lat, lon], radius=acc, color="blue",
                          fill=True, fill_opacity=0.10).add_to(fg_consumers)

# === 新增：輸入座標快速定位 ===
coord_ui = """
{% macro html(this, kwargs) %}
<div style="
  position: fixed;
  top: 10px;
  left: 50px;
  z-index: 9999;
  background-color: white;
  padding: 6px;
  border: 1px solid grey;
  font-size: 14px;
">
  <label><b>輸入座標 (lat,lon):</b></label><br>
  <input type="text" id="coord_input" placeholder="25.04,121.56" style="width:150px"/>
  <button onclick="zoomToCoord()">Go</button>
</div>

<script>
function getMapInstance() {
    // 找出全域變數裡第一個 L.map 物件
    for (var key in window) {
        if (window.hasOwnProperty(key) && window[key] instanceof L.Map) {
            return window[key];
        }
    }
    return null;
}

function zoomToCoord() {
    var val = document.getElementById("coord_input").value;
    if (!val) return;
    var parts = val.split(",");
    if (parts.length != 2) { alert("格式錯誤，請輸入: lat,lon"); return; }
    var lat = parseFloat(parts[0].trim());
    var lon = parseFloat(parts[1].trim());
    if (isNaN(lat) || isNaN(lon)) { alert("座標錯誤"); return; }

    var map = getMapInstance();
    if (!map) { alert("找不到地圖物件"); return; }

    map.flyTo([lat, lon], 16);

    // 臨時 marker
    if (window.tempMarker) {
        map.removeLayer(window.tempMarker);
    }
    window.tempMarker = L.marker([lat, lon]).addTo(map)
        .bindPopup("定位到: " + lat.toFixed(6) + ", " + lon.toFixed(6)).openPopup();
}
</script>
{% endmacro %}
"""

macro = MacroElement()
macro._template = Template(coord_ui)
m.get_root().add_child(macro)


# 加入圖層控制
fg_consumers.add_to(m)
fg_consultY.add_to(m)
fg_clinics.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)


m.save("map_with_clinic_circles.html")
print("已輸出：map_with_clinic_circles.html")
