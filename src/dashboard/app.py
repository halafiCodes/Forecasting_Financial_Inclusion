from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


st.set_page_config(page_title="Ethiopia FI Dashboard", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
	root = Path(__file__).resolve().parents[2]
	data_path = root / "data" / "raw" / "ethiopia_fi_unified_data.csv"
	df = pd.read_csv(data_path)
	for col in ["observation_date", "period_start", "period_end"]:
		if col in df.columns:
			df[col] = pd.to_datetime(df[col], errors="coerce")
	df["year"] = df["observation_date"].dt.year
	return df


def latest_value(df: pd.DataFrame, code: str, gender: str | None = None) -> float | None:
	subset = df[(df["indicator_code"] == code) & (df["record_type"] == "observation")]
	if gender:
		subset = subset[subset["gender"] == gender]
	subset = subset.dropna(subset=["value_numeric", "observation_date"]).sort_values("observation_date")
	if subset.empty:
		return None
	return float(subset.iloc[-1]["value_numeric"])


def trend_growth(df: pd.DataFrame, code: str, gender: str = "all") -> float | None:
	subset = df[(df["indicator_code"] == code) & (df["gender"] == gender) & (df["record_type"] == "observation")]
	subset = subset.dropna(subset=["value_numeric", "observation_date"]).sort_values("observation_date")
	if len(subset) < 2:
		return None
	return float(subset.iloc[-1]["value_numeric"] - subset.iloc[-2]["value_numeric"])


def fit_linear_forecast(series_df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
	series_df = series_df.dropna(subset=["year", "value_numeric"]).copy()
	X = series_df["year"].values
	y = series_df["value_numeric"].values
	if len(series_df) < 2:
		return pd.DataFrame({"year": years, "forecast": np.nan, "ci_low": np.nan, "ci_high": np.nan})
	slope, intercept = np.polyfit(X, y, 1)
	preds = intercept + slope * np.array(years)
	residuals = y - (intercept + slope * X)
	sigma = residuals.std(ddof=1) if len(residuals) > 1 else 0
	ci_low = preds - 1.96 * sigma
	ci_high = preds + 1.96 * sigma
	return pd.DataFrame({"year": years, "forecast": preds, "ci_low": ci_low, "ci_high": ci_high})


def build_event_effects(df: pd.DataFrame, target_code: str) -> pd.Series:
	events = df[df["record_type"] == "event"].copy()
	links = df[df["record_type"] == "impact_link"].copy()
	if events.empty or links.empty:
		return pd.Series(dtype=float)
	joined = links.merge(
		events[["record_id", "observation_date", "indicator"]],
		left_on="parent_id",
		right_on="record_id",
		how="left",
		suffixes=("", "_event"),
	)
	magnitude_map = {"high": 0.15, "medium": 0.08, "low": 0.03, "negligible": 0.01}
	direction_map = {"increase": 1, "decrease": -1, "stabilize": 0, "mixed": 0}
	joined["effect_size"] = joined["impact_magnitude"].map(magnitude_map).fillna(0.0)
	joined["direction_sign"] = joined["impact_direction"].map(direction_map).fillna(0.0)
	joined["effect"] = joined["effect_size"] * joined["direction_sign"]
	joined["lag_months_num"] = pd.to_numeric(joined["lag_months"], errors="coerce").fillna(0)

	def effect_series(event_date: pd.Timestamp, effect: float, lag_months: float) -> pd.Series:
		if pd.isna(event_date):
			return pd.Series(dtype=float)
		start = (event_date + pd.DateOffset(months=int(lag_months))).year
		years = np.arange(start, start + 3)
		ramp = np.linspace(0.3, 1.0, 3)
		return pd.Series(effect * ramp, index=years)

	effects = []
	for _, row in joined[joined["related_indicator"] == target_code].iterrows():
		series = effect_series(row["observation_date"], row["effect"], row["lag_months_num"])
		for year, val in series.items():
			effects.append({"year": year, "effect": val})

	if not effects:
		return pd.Series(dtype=float)
	return pd.DataFrame(effects).groupby("year")["effect"].sum()


data = load_data()
obs = data[data["record_type"] == "observation"].copy()

st.title("Ethiopia Financial Inclusion Dashboard")

tabs = st.tabs(["Overview", "Trends", "Forecasts", "Inclusion Projections"])

with tabs[0]:
	st.subheader("Overview")
	col1, col2, col3, col4 = st.columns(4)

	acc_latest = latest_value(data, "ACC_OWNERSHIP", "all")
	mm_latest = latest_value(data, "ACC_MM_ACCOUNT", "all")
	p2p_atm = latest_value(data, "USG_CROSSOVER", "all")
	telebirr_users = latest_value(data, "USG_TELEBIRR_USERS", "all")

	col1.metric("Account Ownership (%)", f"{acc_latest:.1f}" if acc_latest is not None else "N/A")
	col2.metric("Mobile Money Account Rate (%)", f"{mm_latest:.2f}" if mm_latest is not None else "N/A")
	col3.metric("P2P/ATM Crossover Ratio", f"{p2p_atm:.2f}" if p2p_atm is not None else "N/A")
	col4.metric("Telebirr Users", f"{telebirr_users:,.0f}" if telebirr_users is not None else "N/A")

	st.markdown("### Growth Rate Highlights")
	growth_acc = trend_growth(data, "ACC_OWNERSHIP")
	growth_mm = trend_growth(data, "ACC_MM_ACCOUNT")
	st.write(f"Account ownership last-step change: {growth_acc:+.1f} pp" if growth_acc is not None else "Account ownership change: N/A")
	st.write(f"Mobile money account last-step change: {growth_mm:+.2f} pp" if growth_mm is not None else "Mobile money account change: N/A")

	st.markdown("### Data Download")
	csv_buf = io.StringIO()
	data.to_csv(csv_buf, index=False)
	st.download_button("Download unified dataset", data=csv_buf.getvalue(), file_name="ethiopia_fi_unified_data.csv")

with tabs[1]:
	st.subheader("Trends")
	indicators = obs["indicator_code"].dropna().unique().tolist()
	default_indicators = [code for code in ["ACC_OWNERSHIP", "ACC_MM_ACCOUNT", "USG_P2P_COUNT", "USG_ATM_COUNT"] if code in indicators]
	selected = st.multiselect("Select indicators", indicators, default=default_indicators)

	date_range = st.slider(
		"Year range",
		int(obs["year"].min()),
		int(obs["year"].max()),
		(int(obs["year"].min()), int(obs["year"].max())),
	)

	trend_df = obs[obs["indicator_code"].isin(selected)].copy()
	trend_df = trend_df[(trend_df["year"] >= date_range[0]) & (trend_df["year"] <= date_range[1])]

	fig, ax = plt.subplots(figsize=(8, 4))
	for code in selected:
		sub = trend_df[trend_df["indicator_code"] == code]
		ax.plot(sub["observation_date"], sub["value_numeric"], marker="o", label=code)
	ax.set_title("Indicator Trends")
	ax.set_xlabel("Date")
	ax.set_ylabel("Value")
	ax.legend()
	st.pyplot(fig)

	st.markdown("### Channel Comparison")
	channel = obs[obs["indicator_code"].isin(["USG_P2P_COUNT", "USG_ATM_COUNT"])].copy()
	if not channel.empty:
		fig2, ax2 = plt.subplots(figsize=(8, 4))
		for code in ["USG_P2P_COUNT", "USG_ATM_COUNT"]:
			sub = channel[channel["indicator_code"] == code]
			ax2.plot(sub["observation_date"], sub["value_numeric"], marker="o", label=code)
		ax2.set_title("P2P vs ATM Transaction Counts")
		ax2.set_xlabel("Date")
		ax2.set_ylabel("Transactions")
		ax2.legend()
		st.pyplot(fig2)
	else:
		st.info("No channel comparison data available.")

with tabs[2]:
	st.subheader("Forecasts")
	forecast_years = [2025, 2026, 2027]

	access_series = obs[(obs["indicator_code"] == "ACC_OWNERSHIP") & (obs["gender"] == "all")]
	usage_series = obs[obs["indicator_code"].isin(["USG_DIGITAL_PAYMENT", "ACC_MM_ACCOUNT"])].copy()
	if "USG_DIGITAL_PAYMENT" in usage_series["indicator_code"].unique():
		usage_series = usage_series[usage_series["indicator_code"] == "USG_DIGITAL_PAYMENT"]
		usage_label = "USG_DIGITAL_PAYMENT"
	else:
		usage_series = usage_series[usage_series["indicator_code"] == "ACC_MM_ACCOUNT"]
		usage_label = "ACC_MM_ACCOUNT (proxy)"

	access_fc = fit_linear_forecast(access_series, forecast_years)
	usage_fc = fit_linear_forecast(usage_series, forecast_years)

	use_events = st.checkbox("Include event effects", value=True)
	if use_events:
		access_effects = build_event_effects(data, "ACC_OWNERSHIP")
		usage_effects = build_event_effects(data, "ACC_MM_ACCOUNT")
		access_fc["forecast_event"] = access_fc["forecast"] + access_fc["year"].map(access_effects).fillna(0)
		usage_fc["forecast_event"] = usage_fc["forecast"] + usage_fc["year"].map(usage_effects).fillna(0)
	else:
		access_fc["forecast_event"] = access_fc["forecast"]
		usage_fc["forecast_event"] = usage_fc["forecast"]

	fig3, ax3 = plt.subplots(figsize=(8, 4))
	ax3.plot(access_series["year"], access_series["value_numeric"], marker="o", label="Observed")
	ax3.plot(access_fc["year"], access_fc["forecast_event"], marker="o", label="Forecast")
	ax3.fill_between(access_fc["year"], access_fc["ci_low"], access_fc["ci_high"], alpha=0.2)
	ax3.set_title("Account Ownership Forecast")
	ax3.set_xlabel("Year")
	ax3.set_ylabel("% of adults")
	ax3.legend()
	st.pyplot(fig3)

	fig4, ax4 = plt.subplots(figsize=(8, 4))
	ax4.plot(usage_series["year"], usage_series["value_numeric"], marker="o", label="Observed")
	ax4.plot(usage_fc["year"], usage_fc["forecast_event"], marker="o", label="Forecast")
	ax4.fill_between(usage_fc["year"], usage_fc["ci_low"], usage_fc["ci_high"], alpha=0.2)
	ax4.set_title(f"Digital Payment Usage Forecast ({usage_label})")
	ax4.set_xlabel("Year")
	ax4.set_ylabel("% of adults")
	ax4.legend()
	st.pyplot(fig4)

	st.markdown("### Forecast Table")
	st.dataframe(
		access_fc.merge(usage_fc, on="year", suffixes=("_access", "_usage")),
		use_container_width=True,
	)

with tabs[3]:
	st.subheader("Inclusion Projections")
	scenario = st.selectbox("Scenario", ["pessimistic", "base", "optimistic"], index=1)
	scenario_factors = {"pessimistic": 0.85, "base": 1.0, "optimistic": 1.15}

	access_series = obs[(obs["indicator_code"] == "ACC_OWNERSHIP") & (obs["gender"] == "all")]
	access_fc = fit_linear_forecast(access_series, [2025, 2026, 2027])
	access_fc["scenario"] = access_fc["forecast"] * scenario_factors[scenario]

	target = 60
	latest = latest_value(data, "ACC_OWNERSHIP", "all") or 0
	st.metric("Latest account ownership", f"{latest:.1f}%")
	st.progress(min(latest / target, 1.0))

	fig5, ax5 = plt.subplots(figsize=(8, 4))
	ax5.plot(access_series["year"], access_series["value_numeric"], marker="o", label="Observed")
	ax5.plot(access_fc["year"], access_fc["scenario"], marker="o", label=f"Scenario: {scenario}")
	ax5.axhline(target, color="red", linestyle="--", label="60% target")
	ax5.set_title("Inclusion Projections")
	ax5.set_xlabel("Year")
	ax5.set_ylabel("% of adults")
	ax5.legend()
	st.pyplot(fig5)
