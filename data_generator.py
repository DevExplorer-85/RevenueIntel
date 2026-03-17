import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)

PLANS = {
    "Starter":    {"price": 49,   "churn_rate": 0.07, "expansion_prob": 0.08},
    "Growth":     {"price": 149,  "churn_rate": 0.05, "expansion_prob": 0.12},
    "Pro":        {"price": 399,  "churn_rate": 0.03, "expansion_prob": 0.15},
    "Enterprise": {"price": 1199, "churn_rate": 0.02, "expansion_prob": 0.10},
}

PLAN_NAMES = list(PLANS.keys())
PLAN_DIST   = [0.40, 0.30, 0.20, 0.10]

INDUSTRIES = ["FinTech", "HealthTech", "EdTech", "E-Commerce", "DevTools", "MarTech", "HRTech"]
REGIONS    = ["North America", "Europe", "Asia-Pacific", "Latin America", "India"]

def generate_customers(n=400, start_date=datetime(2022, 1, 1), end_date=datetime(2024, 12, 31)):
    customers = []
    total_days = (end_date - start_date).days

    for i in range(n):
        # Skew acquisition toward recent months (growth trend)
        raw_day = int(np.random.beta(1.5, 1.0) * total_days)
        acq_date = start_date + timedelta(days=raw_day)

        plan = np.random.choice(PLAN_NAMES, p=PLAN_DIST)
        info = PLANS[plan]

        # Tenure in months from acquisition to end
        max_tenure = max(1, (end_date.year - acq_date.year) * 12 + (end_date.month - acq_date.month))
        churn_month = None
        for m in range(1, max_tenure + 1):
            if random.random() < info["churn_rate"]:
                churn_month = m
                break

        churn_date = None
        if churn_month:
            churn_date = acq_date + timedelta(days=churn_month * 30)
            if churn_date > end_date:
                churn_date = None

        customers.append({
            "customer_id":  f"CUST-{i+1:04d}",
            "acquisition_date": acq_date,
            "churn_date":   churn_date,
            "plan":         plan,
            "base_price":   info["price"],
            "industry":     random.choice(INDUSTRIES),
            "region":       random.choice(REGIONS),
            "expansion_prob": info["expansion_prob"],
        })

    return pd.DataFrame(customers)


def generate_mrr_records(customers: pd.DataFrame,
                         start_date=datetime(2022, 1, 1),
                         end_date=datetime(2024, 12, 31)):
    records = []
    months = pd.date_range(start=start_date, end=end_date, freq="MS")

    for _, cust in customers.iterrows():
        price = cust["base_price"]
        active = False

        for month in months:
            acq = cust["acquisition_date"].replace(day=1)
            if pd.Timestamp(month) < pd.Timestamp(acq):
                continue

            churn = cust["churn_date"]
            if churn is not None and pd.Timestamp(month) >= pd.Timestamp(churn).replace(day=1):
                if active:
                    records.append({
                        "month": month, "customer_id": cust["customer_id"],
                        "plan": cust["plan"], "mrr": 0,
                        "mrr_type": "Churned", "industry": cust["industry"],
                        "region": cust["region"],
                    })
                    active = False
                break

            if not active:
                mrr_type = "New"
                active = True
            else:
                # Expansion / Contraction / Retained
                r = random.random()
                if r < cust["expansion_prob"]:
                    expansion = round(price * random.uniform(0.10, 0.30), 2)
                    price += expansion
                    mrr_type = "Expansion"
                elif r < cust["expansion_prob"] + 0.04:
                    contraction = round(price * random.uniform(0.05, 0.15), 2)
                    price = max(cust["base_price"] * 0.5, price - contraction)
                    mrr_type = "Contraction"
                else:
                    mrr_type = "Retained"

            records.append({
                "month": month, "customer_id": cust["customer_id"],
                "plan": cust["plan"], "mrr": round(price, 2),
                "mrr_type": mrr_type, "industry": cust["industry"],
                "region": cust["region"],
            })

    return pd.DataFrame(records)


def build_monthly_summary(records: pd.DataFrame) -> pd.DataFrame:
    active = records[records["mrr"] > 0]
    churned = records[records["mrr_type"] == "Churned"]

    summary = active.groupby("month").agg(
        total_mrr=("mrr", "sum"),
        active_customers=("customer_id", "nunique"),
    ).reset_index()

    new_mrr = active[active["mrr_type"] == "New"].groupby("month")["mrr"].sum().rename("new_mrr")
    exp_mrr = active[active["mrr_type"] == "Expansion"].groupby("month")["mrr"].sum().rename("expansion_mrr")
    con_mrr = active[active["mrr_type"] == "Contraction"].groupby("month")["mrr"].sum().rename("contraction_mrr")
    churn_mrr = churned.groupby("month")["mrr"].sum().rename("churned_mrr")  # will be 0, use prev month ref

    summary = summary.merge(new_mrr, on="month", how="left")
    summary = summary.merge(exp_mrr, on="month", how="left")
    summary = summary.merge(con_mrr, on="month", how="left")
    summary = summary.merge(churn_mrr, on="month", how="left")
    summary = summary.fillna(0)

    summary["arr"] = summary["total_mrr"] * 12
    summary["arpu"] = summary["total_mrr"] / summary["active_customers"]
    summary["mom_growth"] = summary["total_mrr"].pct_change() * 100
    summary["net_new_mrr"] = summary["new_mrr"] + summary["expansion_mrr"] - summary["contraction_mrr"] - summary["churned_mrr"]

    return summary


def build_cohort_data(records: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    active = records[records["mrr"] > 0].copy()
    acq_map = customers.set_index("customer_id")["acquisition_date"].apply(
        lambda d: d.replace(day=1)
    ).to_dict()

    active["cohort"] = active["customer_id"].map(acq_map)
    active["cohort"] = pd.to_datetime(active["cohort"])
    active["month"]  = pd.to_datetime(active["month"])
    active["period"]  = ((active["month"].dt.year - active["cohort"].dt.year) * 12 +
                         (active["month"].dt.month - active["cohort"].dt.month))

    # MRR retention by cohort
    cohort_base = active[active["period"] == 0].groupby("cohort")["mrr"].sum().rename("base_mrr")
    cohort_mrr  = active.groupby(["cohort", "period"])["mrr"].sum().reset_index()
    cohort_mrr  = cohort_mrr.merge(cohort_base, on="cohort")
    cohort_mrr["retention_pct"] = (cohort_mrr["mrr"] / cohort_mrr["base_mrr"] * 100).round(1)

    # Keep only cohorts with enough data (at least 6 months)
    cohort_sizes = cohort_mrr.groupby("cohort")["period"].max()
    valid_cohorts = cohort_sizes[cohort_sizes >= 6].index
    cohort_mrr = cohort_mrr[cohort_mrr["cohort"].isin(valid_cohorts)]

    return cohort_mrr


if __name__ == "__main__":
    print("Generating dataset...")
    customers = generate_customers(400)
    records   = generate_mrr_records(customers)
    summary   = build_monthly_summary(records)
    cohort    = build_cohort_data(records, customers)

    customers.to_csv("data/customers.csv", index=False)
    records.to_csv("data/mrr_records.csv", index=False)
    summary.to_csv("data/monthly_summary.csv", index=False)
    cohort.to_csv("data/cohort_data.csv", index=False)
    print(f"Done. {len(customers)} customers, {len(records)} records.")
