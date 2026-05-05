if not df.empty:
                # Menghitung rasio volume (LENGKAP)
                df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
                
                # Filter Market Cap & Volume
                df = df[(df['market_cap_basic'] >= 5e11) & (df['v_ratio'] >= 1.5)]
                df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                pesan_tele = f"⚡ <b>GOD MODE RADAR</b>\n"
                
                for idx, row in df.iterrows():
                    res = get_analysis(row['name'], row)
                    if res:
                        # ... (kode seterusnya hingga except)