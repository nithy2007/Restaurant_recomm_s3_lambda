from flask import Flask, render_template, request
import os
from get_restaurant_recom_cloud import get_top_restaurants
import awsgi
import boto3

app = Flask(__name__)

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "s3-restaurant-recom-data")
s3_client = boto3.client("s3")

def load_txt_from_s3(bucket_name: str, key: str) -> list:
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    content = response["Body"].read().decode("utf-8")
    return [line.strip() for line in content.splitlines() if line.strip()]

city_list = load_txt_from_s3(S3_BUCKET_NAME, "city_list.txt")
dish_list = load_txt_from_s3(S3_BUCKET_NAME, "dish_list.txt")

@app.route("/restaurant_recommendation")
def home():
    return render_template("rest_recom_cloud.html", city=city_list, dish=dish_list)

@app.route("/get_recommendations", methods=["POST"])
def recommend():
    city = request.form.get("city")
    dish = request.form.get("dish")

    base_path="data"
    results = get_top_restaurants(city, dish,10)
    if not results:
        return render_template("recommendation_result_cloud.html", recommendations=[],
                                                            selected_dish=dish,
                                                            selected_city=city,
                               message=f"Could not find restaurants that serve {dish} in {city}. Please try a different dish or city."
        )
    else:
        return render_template("recommendation_result_cloud.html", recommendations=results,
                                                            selected_dish=dish,
                                                            selected_city=city)

def lambda_handler(event, context):
    return awsgi.response(app, event, context)


if __name__ == "__main__":
    app.run(debug=True)
