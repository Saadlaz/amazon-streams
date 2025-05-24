# reviews/views.py

from django.shortcuts import render
from .mongo import collection   # your MongoDB collection
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import json
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def dashboard(request):
    # --- 1) Fetch your test‐set reviews (isTest=True) for the last 30 days
    since = datetime.utcnow() - timedelta(days=30)
    cursor = collection.find({
        "isTest": True,
        "timestamp": {"$gte": since}
    })
    reviews = list(cursor)

    # --- 2) Compute overall counts & rates
    total = len(reviews)
    pos = sum(1 for r in reviews if r["sentiment"] == "positive")
    neg = sum(1 for r in reviews if r["sentiment"] == "negative")
    neu = sum(1 for r in reviews if r["sentiment"] == "neutral")

    positive_rate = (pos / total * 100) if total else 0
    negative_rate = (neg / total * 100) if total else 0

    sentiment_data = {
        "positive": pos,
        "neutral":  neu,
        "negative": neg
    }

    # --- 3) Reviews per day (last 7 days)
    N = 7
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=N - 1)
    dates = [(start_date + timedelta(days=i)).isoformat() for i in range(N)]

    counts_by_date = defaultdict(int)
    for r in reviews:
        day = r["timestamp"].strftime("%Y-%m-%d")
        if day in dates:
            counts_by_date[day] += 1
    counts = [counts_by_date.get(d, 0) for d in dates]

    # --- 4) Sentiment over time (monthly buckets)
    month_buckets = defaultdict(lambda: {"positive":0, "neutral":0, "negative":0})
    for r in reviews:
        m = r["timestamp"].strftime("%Y-%m")
        month_buckets[m][r["sentiment"]] += 1
    ordered_months = OrderedDict(sorted(month_buckets.items()))
    months = list(ordered_months.keys())
    sentiment_over_time = {
        "positive": [ordered_months[m]["positive"] for m in months],
        "neutral":  [ordered_months[m]["neutral"]  for m in months],
        "negative": [ordered_months[m]["negative"] for m in months],
    }

    # --- 5) Render template
    return render(request, "reviews/OfflineDashboard.html", {
        "total_reviews": total,
        "positive_rate": f"{positive_rate:.2f}",
        "negative_rate": f"{negative_rate:.2f}",
        "sentiment_data": sentiment_data,
        "dates": dates,
        "counts": counts,
        "months": months,
        "sentiment_over_time": sentiment_over_time,
    })
def auto_refresh_dashboard(request):
    since = datetime.utcnow() - timedelta(days=30)
    cursor = collection.find({
        "isTest": True,
        "timestamp": {"$gte": since}
    })
    reviews = list(cursor)

    total = len(reviews)
    pos = sum(1 for r in reviews if r["sentiment"] == "positive")
    neg = sum(1 for r in reviews if r["sentiment"] == "negative")
    neu = sum(1 for r in reviews if r["sentiment"] == "neutral")

    positive_rate = (pos / total * 100) if total else 0
    negative_rate = (neg / total * 100) if total else 0

    sentiment_data = {
        "positive": pos,
        "neutral":  neu,
        "negative": neg
    }

    # Last 7 days
    N = 7
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=N - 1)
    dates = [(start_date + timedelta(days=i)).isoformat() for i in range(N)]

    counts_by_date = defaultdict(int)
    for r in reviews:
        day = r["timestamp"].strftime("%Y-%m-%d")
        if day in dates:
            counts_by_date[day] += 1
    counts = [counts_by_date.get(d, 0) for d in dates]

    # Monthly sentiment
    month_buckets = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
    for r in reviews:
        m = r["timestamp"].strftime("%Y-%m")
        month_buckets[m][r["sentiment"]] += 1
    ordered_months = OrderedDict(sorted(month_buckets.items()))
    months = list(ordered_months.keys())
    sentiment_over_time = {
        "positive": [ordered_months[m]["positive"] for m in months],
        "neutral": [ordered_months[m]["neutral"] for m in months],
        "negative": [ordered_months[m]["negative"] for m in months],
    }

    return render(request, "reviews/OnlineDashboard.html", {
        "total_reviews": total,
        "positive_rate": f"{positive_rate:.2f}",
        "negative_rate": f"{negative_rate:.2f}",
        "sentiment_data": sentiment_data,
        "dates": dates,
        "counts": counts,
        "months": months,
        "sentiment_over_time": sentiment_over_time,
    })


# Online view
def online(request):
    return render(request, 'reviews/OnlineDashboard.html')


@csrf_exempt
def push_review(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "bad json"}, status=400)

    async_to_sync(get_channel_layer().group_send)(
        "reviews", {"type": "broadcast.review", "payload": payload}
    )
    return JsonResponse({"status": "ok"})