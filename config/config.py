AWS_ACCESS_KEY_ID = 'ASIASSNXS3TDQRHIEMCR'
AWS_SECRET_ACCESS_KEY = '75k2s69XRdI6L8xkLtXY7x5U6fU4a23/JcRbNBeZ'
AWS_SESSION_TOKEN = 'FwoGZXIvYXdzEEQaDMkJ/lQCcORxLsFXpSLIAXAA/h5f/hsxzrOJk2St4Sf1splqlJwUZicKpFyHB9isUrffsUM9PwHceVTOcmSiMAlrd05IgcijYwUNuzfVH7AZ5BSQ/31iEzXQoqFke9hCCrqMrxTE2fVpYD0C4/SUJFyS9h3h5a6fiUsiscqLl/+cILBjSyPzUSsIEDhFCGT98dVYo629IwOr0RrLobfLiFKnMM2Jb2I2qp3GJn8fm3Ki2keEdHhX2WTa/lMFsGD62pFPMeWJk87O/+5vU+tTbvtVXfQVaN9qKPnfpPMFMi3GaUJu9zrJWCVpuk4KgTc1Hu5nMoI1PAir0gIMjrjge/40AvI7ug9ypXXtkqU='
AMI = 'ami-0dec3aa383f82116a'
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
