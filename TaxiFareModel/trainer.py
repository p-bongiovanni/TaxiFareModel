from cProfile import run
from sklearn.pipeline import Pipeline
from sklearn import set_config; set_config(display='diagram')
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from TaxiFareModel.data import get_data, clean_data
from TaxiFareModel.encoders import TimeFeaturesEncoder,haversine_vectorized, DistanceTransformer
from TaxiFareModel.utils import *
from sklearn.model_selection import train_test_split
import numpy as np
from memoized_property import memoized_property
import mlflow
from mlflow.tracking import MlflowClient
import joblib

class Trainer():

    EXPERIMENT_NAME = "[PT] [Lisbon] [FatT0ny1] TaxiFareModel.1"
    MLFLOW_URI = "https://mlflow.lewagon.ai/"

    def __init__(self, X, y):
        """
            X: pandas DataFrame
            y: pandas Series
        """
        self.pipeline = None
        self.X = X
        self.y = y

    def set_pipeline(self):

        dist_pipe = Pipeline([
            ('dist_trans', DistanceTransformer()),
            ('stdscaler', StandardScaler())])

        time_pipe = Pipeline([
            ('time_enc', TimeFeaturesEncoder('pickup_datetime')),
            ('ohe', OneHotEncoder(handle_unknown='ignore'))])

        preproc_pipe = ColumnTransformer([
            ('distance', dist_pipe, ["pickup_latitude", "pickup_longitude", 'dropoff_latitude', 'dropoff_longitude']),
            ('time', time_pipe, ['pickup_datetime'])], remainder="drop")

        pipe = Pipeline([
            ('preproc', preproc_pipe),
            ('linear_model', LinearRegression())])

        return pipe

    def run(self):
        """set and train the pipeline"""
        self.pipe = self.set_pipeline()
        self.pipe.fit(self.X, self.y)
        self.mlflow_log_param('Params', 'linear')

    def evaluate(self, X_test, y_test):
        """evaluates the pipeline on df_test and return the RMSE"""

        y_pred = self.pipe.predict(X_test)
        rmse = np.sqrt(((y_pred - y_test)**2).mean())
        self.mlflow_log_metric('RMSE', rmse)

    def save_model(self):
        """ Save the trained model into a model.joblib file """
        joblib.dump(self.pipe, 'model.joblib')

    @memoized_property
    def mlflow_client(self):
        mlflow.set_tracking_uri(self.MLFLOW_URI)
        return MlflowClient()

    @memoized_property
    def mlflow_experiment_id(self):
        try:
            return self.mlflow_client.create_experiment(self.EXPERIMENT_NAME)
        except BaseException:
            return self.mlflow_client.get_experiment_by_name(self.EXPERIMENT_NAME).experiment_id

    @memoized_property
    def mlflow_run(self):
        return self.mlflow_client.create_run(self.mlflow_experiment_id)

    def mlflow_log_param(self, key, value):
        self.mlflow_client.log_param(self.mlflow_run.info.run_id, key, value)

    def mlflow_log_metric(self, key, value):
        self.mlflow_client.log_metric(self.mlflow_run.info.run_id, key, value)




if __name__ == "__main__":
    N = 10_000
    df = get_data(nrows=N)
    df = clean_data(df)
    y = df["fare_amount"]
    X = df.drop("fare_amount", axis=1)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
    trainer = Trainer(X_train, y_train)
    trainer.run()
    trainer.evaluate(X_test, y_test)
    trainer.save_model()
