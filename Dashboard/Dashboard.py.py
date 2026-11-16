import os
from pathlib import Path

data_dir = Path("./data")
data_dir.mkdir(parents=True, exist_ok=True)

print(f"Directory created at: {data_dir.resolve()}")
print("Please upload 'MainData_ecommerce_eda.csv' and 'MainData_customer_rfm.csv' into this folder using the Colab file explorer on the left.")

%%writefile app.py
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Olist E-Commerce Dashboard", page_icon="📊", layout="wide")


# Membaca data relatif dari folder tempat app.py berada
DATA_DIR = Path(__file__).resolve().parent / "data"

 @st.cache_data
 def load_data():
     sales = pd.read_csv(DATA_DIR / "MainData_ecommerce_eda.csv", parse_dates=["order_purchase_timestamp"])
     customers = pd.read_csv(DATA_DIR / "MainData_customer_rfm.csv")
     return sales, customers
 
 try:
     sales, rfm = load_data()
 except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
     st.error(f"Dataset tidak dapat dibaca: {error}")
     st.info("Simpan MainData_ecommerce_eda.csv dan MainData_customer_rfm.csv di folder Dashboard/data/.")
     st.stop()
 
 sales_columns = {"order_id", "customer_unique_id", "order_purchase_timestamp", "price", "product_category_name_english"}
 rfm_columns = {"customer_unique_id", "segmentasi", "recency", "frequency", "monetary"}
 missing_sales = sales_columns - set(sales.columns)
 missing_rfm = rfm_columns - set(rfm.columns)
 if missing_sales or missing_rfm:
     st.error(f"Kolom yang belum tersedia — transaksi: {sorted(missing_sales)}; RFM: {sorted(missing_rfm)}")
     st.stop()
 
 sales["price"] = pd.to_numeric(sales["price"], errors="coerce")
 sales = sales.dropna(subset=["order_purchase_timestamp", "price", "order_id"])
 sales = sales[sales["price"] >= 0].copy()
 
 st.title("Olist E-Commerce Analytics Dashboard")
 st.caption("Kinerja penjualan, kategori produk, dan segmentasi pelanggan berdasarkan dataset Olist")
 
 halaman = st.sidebar.radio(
     "Pilih analisis", ["Sales Performance", "Product Performance", "Customer Segmentation"])
 if halaman != "Customer Segmentation":
     if sales.empty:
         st.warning("Tidak ada transaksi yang dapat ditampilkan.")
         st.stop()
 
     min_date = sales["order_purchase_timestamp"].min().date()
     max_date = sales["order_purchase_timestamp"].max().date()
     periode = st.sidebar.date_input(
         "Periode transaksi", value=(min_date, max_date), min_value=min_date, max_value=max_date)
     if len(periode) != 2:
         st.info("Pilih tanggal awal dan akhir untuk menampilkan analisis.")
         st.stop()
     awal, akhir = periode
     filtered = sales.loc[sales["order_purchase_timestamp"].dt.date.between(awal, akhir)].copy()
     if filtered.empty:
         st.warning("Tidak ada transaksi dalam periode yang dipilih.")
         st.stop()
 
     total_penjualan = filtered["price"].sum()
     jumlah_pesanan = filtered["order_id"].nunique()
     pelanggan_unik = filtered["customer_unique_id"].nunique()
     k1, k2, k3 = st.columns(3)
     k1.metric("Nilai penjualan produk", f"R$ {total_penjualan:,.2f}")
     k2.metric("Pesanan unik", f"{jumlah_pesanan:,}")
     k3.metric("Pelanggan unik", f"{pelanggan_unik:,}")
     st.caption("Nilai penjualan merupakan jumlah price produk pada pesanan delivered, tanpa ongkos kirim.")
 
     if halaman == "Sales Performance":
         st.subheader("Tren penjualan bulanan")
         bulanan = (
             filtered.assign(bulan=filtered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp())
             .groupby("bulan", as_index=False)
             .agg(nilai_penjualan=("price", "sum"), jumlah_pesanan=("order_id", "nunique"))
             .sort_values("bulan"))
         fig = px.line(bulanan, x="bulan", y="nilai_penjualan", markers=True,
                       labels={"bulan": "Bulan", "nilai_penjualan": "Penjualan produk (R$)"})
         st.plotly_chart(fig, use_container_width=True)
         fig2 = px.line(bulanan, x="bulan", y="jumlah_pesanan", markers=True,
                        labels={"bulan": "Bulan", "jumlah_pesanan": "Pesanan unik"})
         st.plotly_chart(fig2, use_container_width=True)
         puncak = bulanan.loc[bulanan["nilai_penjualan"].idxmax()]
         st.write(f"**Insight:** Penjualan terbesar dalam periode terpilih terjadi pada "
                  f"{puncak['bulan']:%B %Y}, sebesar R$ {puncak['nilai_penjualan']:,.2f}.")
         st.caption("Bulan awal atau akhir mungkin tidak lengkap; bandingkan periode dengan hati-hati.")
 
     else:
         st.subheader("Kategori produk berdasarkan nilai penjualan")
         kategori = (
             filtered.assign(kategori=filtered["product_category_name_english"].fillna("Unknown"))
             .groupby("kategori", as_index=False)
             .agg(nilai_penjualan=("price", "sum"), jumlah_item=("order_id", "size"))
             .sort_values("nilai_penjualan", ascending=False))
         top10 = kategori.head(10).sort_values("nilai_penjualan")
         fig = px.bar(top10, x="nilai_penjualan", y="kategori", orientation="h",
                      labels={"kategori": "Kategori", "nilai_penjualan": "Penjualan produk (R$)"})
         st.plotly_chart(fig, use_container_width=True)
         utama = kategori.iloc[0]
         kontribusi = utama["nilai_penjualan"] / total_penjualan * 100 if total_penjualan else 0
         st.write(f"**Insight:** Kategori **{utama['kategori']}** menyumbang "
                  f"{kontribusi:.2f}% nilai penjualan produk pada periode terpilih.")
         st.dataframe(kategori, use_container_width=True, hide_index=True)
 
 else:
     st.subheader("Segmentasi pelanggan (RFM)")
     st.info("RFM dihitung dari keseluruhan periode dataset. Filter tanggal penjualan tidak berlaku di halaman ini.")
     if rfm.empty:
         st.warning("Data RFM kosong.")
         st.stop()
     ringkasan = (
         rfm.groupby("segmentasi", as_index=False)
         .agg(jumlah_pelanggan=("customer_unique_id", "nunique"),
              rata_recency=("recency", "mean"),
              rata_frequency=("frequency", "mean"),
              rata_monetary=("monetary", "mean"),
              total_monetary=("monetary", "sum"))
         .sort_values("jumlah_pelanggan", ascending=False))
     fig = px.bar(ringkasan, x="segmentasi", y="jumlah_pelanggan",
                  labels={"segmentasi": "Segmen", "jumlah_pelanggan": "Pelanggan"})
     st.plotly_chart(fig, use_container_width=True)
     st.dataframe(ringkasan.round(2), use_container_width=True, hide_index=True)
     terbesar = ringkasan.iloc[0]
     st.write(f"**Insight:** Segmen **{terbesar['segmentasi']}** memiliki pelanggan terbanyak "
              f"({terbesar['jumlah_pelanggan']:,} pelanggan).")
     st.caption("Skor dan label segmen mengikuti metode RFM dari notebook. Validasi skor Frequency sebelum rekomendasi final.")
 
 st.divider()
 st.caption("Sumber: Brazilian E-Commerce Public Dataset by Olist | Analisis menggunakan Python dan Streamlit")
