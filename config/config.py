AWS_ACCESS_KEY_ID = 'ASIASSNXS3TDYTLOYZMB'
AWS_SECRET_ACCESS_KEY = 'dJGdnXcYw6HqzVbABJ+G0rCtvAb4cXx6uN0qpyzn'
AWS_SESSION_TOKEN = 'FwoGZXIvYXdzEFsaDC46VgVL7QpL6arVrCLIAZwcyg9F4xhZzCFnsKy3EObRccjN0VT8QY0JTmZPzaJ7oTrI/ROoBd4hb1wz0IFyED4Mea4qbXjl69k/TL0fYcieuDA7cOXJqYRD7Zw7H+ZhjnyvpxCN6/k92IGOrqLb6XXw50iROcKbVYB8YFHvkQov5+w9of0E0QRd2oVhFc8PpXl0GnSBCUIWl9GZ2GVtP+6y7t3964Pv7EUqs565wzSV/5nxegaqcBmSpTyjgAQhcTyPQRZtcnFzQtiLeuHdk4+PkYbJIVRPKPbwqfMFMi2rHVcH75gq/w4+kMI8sBaeYHm7zUypl9wSS9Vs1YMf6xYFNBogWrPTyaayRus='
AMI = 'ami-0bf59f3610a724924'
SECURITY_GROUP_IDS = ['sg-05313bb3ee1f2de47']
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
IAM_INSTANCE_PROFILE = {
    'Arn': 'arn:aws:iam::177015545031:instance-profile/FULL_ACCESS',
    'Name': 'FULL_ACCESS'
}
TARGET_GROUP_ARN = 'arn:aws:elasticloadbalancing:us-east-1:177015545031:targetgroup/odwa-group/6ed093f9ee3e5568'
DB_PASSWORD = 'WBGCI3ElWecukBooRzaH'
DB_ENDPOINT = 'odwa-db.c8he8i54iqnw.us-east-1.rds.amazonaws.com'
DB_MASTER = 'admin'
DB_NAME = 'odwadb'
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://{}:{}@{}/{}'.format(
    DB_MASTER, DB_PASSWORD, DB_ENDPOINT, DB_NAME)
SECRET_KEY = 'odwa'
