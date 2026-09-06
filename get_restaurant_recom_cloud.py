import json
import boto3
import io
#import os


# Initialize the S3 client using boto3
s3_client = boto3.client("s3")

# Retrieve bucket name from environment variables
#S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "s3-restaurant-recom-data")

def load_data(bucket_name, target_city):
    target_city_res_reviews = []
    biz_map_name_city = {}

    # 1. Load city business IDs JSON directly from S3
    city_obj = s3_client.get_object(
        Bucket=bucket_name, Key="yelp_city_business_ids.json")
    city_biz_id_data = json.loads(city_obj["Body"].read().decode("utf-8"))

    # Convert to set for O(1) instant lookups
    target_city_biz_ids = set(city_biz_id_data.get(target_city, []))

    if not target_city_biz_ids:
        return target_city_biz_ids, biz_map_name_city, target_city_res_reviews

    # 2. Stream and parse business metadata line-by-line from S3 stream
    biz_obj = s3_client.get_object(
        Bucket=bucket_name, Key="yelp_academic_dataset_business.json"
    )
    for line in io.TextIOWrapper(biz_obj["Body"], encoding="utf-8"):
        if not line.strip():
            continue
        record = json.loads(line)
        biz_id = record.get("business_id")

        if biz_id in target_city_biz_ids:
            biz_map_name_city[biz_id] = (
                record.get("name", "Unknown"),
                record.get("city", "Unknown"),
            )

    # 3. Stream and parse reviews line-by-line from S3 stream
    reviews_obj = s3_client.get_object(
        Bucket=bucket_name,
        Key="sampled_restaurant_reviews_with_sentiment.json",
    )
    for line in io.TextIOWrapper(reviews_obj["Body"], encoding="utf-8"):
        if not line.strip():
            continue
        review = json.loads(line)

        if review.get("business_id") in target_city_biz_ids:
            target_city_res_reviews.append(review)

    return target_city_biz_ids, biz_map_name_city, target_city_res_reviews

def get_top_restaurants(target_city, target_dish,top_n=10):

    target_city_biz_ids, biz_map_name_city, target_city_res_reviews = load_data("s3-restaurant-recom-data", target_city)
    if not target_city_biz_ids:
        return []

    target_dish_lower = target_dish.lower()
    positive_counts = {}

    # Count matching positive reviews
    for review in target_city_res_reviews:
        sentiment = review.get("sentiment", "").upper()
        review_text = review.get("text", "").lower()

        if sentiment == "POSITIVE" and target_dish_lower in review_text:
            biz_id = review.get("business_id")
            positive_counts[biz_id] = positive_counts.get(biz_id, 0) + 1

    # Sort results by count descending and take top N
    sorted_businesses = sorted(
        positive_counts.items(), key=lambda item: item[1], reverse=True
    )[:top_n]

    # Format human-readable output
    results = []
    for biz_id, count in sorted_businesses:
        name, city = biz_map_name_city.get(biz_id, ("Unknown", target_city))
        results.append(f"{name} ({city}) → {count} positive reviews")

    return results
