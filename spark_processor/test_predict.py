from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel

if __name__ == "__main__":
    # 1. Start a local Spark session
    spark = SparkSession.builder \
        .appName("ModelSmokeTest") \
        .master("local[*]") \
        .getOrCreate()

    # 2. Load your RF pipeline (folder name kept as-is)
    model = PipelineModel.load("/app/rf_pipeline_amazon_json")

    # 3. Create a DataFrame of example reviews
    examples = [
        (0, "I absolutely love this product, it works perfectly!"),
        (1, "Terrible quality — broke after one use."),
        (2, "It’s okay, neither great nor terrible."),
    ]
    df = spark.createDataFrame(examples, ["id", "reviewText"])

    # 4. Run the model
    preds = model.transform(df).select("reviewText", "prediction")

    # 5. Show results
    preds.show(truncate=False)

    spark.stop()
