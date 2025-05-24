# spark_processor/test_model.py

from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel, Transformer
from pyspark.ml.param.shared import HasInputCol, HasOutputCol
from pyspark.ml.util import DefaultParamsReadable, DefaultParamsWritable
from pyspark.sql.functions import col, lower, udf
from pyspark.sql.types import ArrayType, StringType
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk

# === Download required NLTK data ===
nltk.download('stopwords')
nltk.download('wordnet')

# === Define UDFs ===
stop_words = set(stopwords.words('english'))
stop_words.remove('not')  # keep "not" for sentiment

def stopwords_remove(tokens):
    return [word for word in tokens if word not in stop_words]
stopwords_remove_udf = udf(stopwords_remove, ArrayType(StringType()))

lemmatizer = WordNetLemmatizer()
def lemmatization(tokens):
    return [lemmatizer.lemmatize(word, pos='v') for word in tokens]
lemmatization_udf = udf(lemmatization, ArrayType(StringType()))

def remove_short_words(tokens):
    return [word for word in tokens if len(word) > 2]
remove_short_words_udf = udf(remove_short_words, ArrayType(StringType()))

# === Define all Custom Transformers ===
class LowerTransformer(Transformer, HasInputCol, HasOutputCol, DefaultParamsWritable, DefaultParamsReadable):
    def __init__(self, inputCol=None, outputCol=None):
        super().__init__()
        self._set(inputCol=inputCol, outputCol=outputCol)

    def _transform(self, dataset):
        return dataset.withColumn(self.getOutputCol(), lower(col(self.getInputCol())))

class StopwordsRemover(Transformer, HasInputCol, HasOutputCol, DefaultParamsWritable, DefaultParamsReadable):
    def __init__(self, inputCol=None, outputCol=None):
        super().__init__()
        self._set(inputCol=inputCol, outputCol=outputCol)

    def _transform(self, dataset):
        return dataset.withColumn(self.getOutputCol(), stopwords_remove_udf(col(self.getInputCol())))

class Lemmatizer(Transformer, HasInputCol, HasOutputCol, DefaultParamsWritable, DefaultParamsReadable):
    def __init__(self, inputCol=None, outputCol=None):
        super().__init__()
        self._set(inputCol=inputCol, outputCol=outputCol)

    def _transform(self, dataset):
        return dataset.withColumn(self.getOutputCol(), lemmatization_udf(col(self.getInputCol())))

class ShortWordRemover(Transformer, HasInputCol, HasOutputCol, DefaultParamsWritable, DefaultParamsReadable):
    def __init__(self, inputCol=None, outputCol=None):
        super().__init__()
        self._set(inputCol=inputCol, outputCol=outputCol)

    def _transform(self, dataset):
        return dataset.withColumn(self.getOutputCol(), remove_short_words_udf(col(self.getInputCol())))

# === Main logic ===
if __name__ == "__main__":
    # Start Spark session
    spark = SparkSession.builder.appName("TestModel").getOrCreate()

    # Load your full saved pipeline model
    model = PipelineModel.load("/app/rf_pipeline_amazon_json")

    # Try to get labels from the final StringIndexer (LogisticRegression model input)
    labels = next((s.labels for s in model.stages if hasattr(s, "labels")), ["negative", "neutral", "positive"])

    # Input sample reviews
    sample_reviews = [
        ("This product is amazing, I love it!",),
        ("Worst thing I've ever bought.",),
        ("It's decent, not bad but not great.",),
    ]

    df = spark.createDataFrame(sample_reviews, ["reviewText"])

    # Transform using the full pipeline
    predictions = model.transform(df)

    # Map numeric prediction to actual string label
    def idx2str(idx):
        try:
            return labels[int(idx)]
        except:
            return "unknown"

    # Show predictions
    results = predictions.select("reviewText", "prediction").collect()
    print("\n=== Pipeline Predictions ===")
    for row in results:
        print(f"{row.reviewText!r}  →  {idx2str(row.prediction)}")

    # Stop Spark
    spark.stop()
