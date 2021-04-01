This repository is attached to the article. 

You can use the SAM template to get everything generated for you (`sam build && sam deploy`). 

The following commands are useful if the S3 bucket already exists and you want to create an Object Lambda Access Point manually.

1. Create an [Access Point](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-access-points.html): 

```
aws s3control create-access-point --account-id 012345678912 --name anonymized-access --bucket my-bucket-with-cid
```

2. Create an [Object Lambda Access Point](https://docs.aws.amazon.com/AmazonS3/latest/userguide/olap-create.html) using the following json file (_anonymize-lambda-accesspoint.json_) and command:

```json
{
    "SupportingAccessPoint" : "arn:aws:s3:eu-central-1:012345678912:accesspoint/anonymized-access",
    "TransformationConfigurations": [{
        "Actions" : ["GetObject"],
        "ContentTransformation" : {
            "AwsLambda": {
                "FunctionArn" : "arn:aws:lambda:eu-central-1:012345678912:function:data-anonymizer-AnonymiserFunction-RTHQH8LO8WN9"
            }
        }
    }]
}
```

```
aws s3control create-access-point-for-object-lambda --account-id 012345678912 --name anonymize-lambda-accesspoint --configuration file://anonymize-lambda-accesspoint.json
```

Finally test:

```
 aws s3api get-object --bucket arn:aws:s3-object-lambda:eu-central-1:012345678912:accesspoint/anonymize-lambda-accesspoint --key patients.csv ~/Downloads/anonymized.csv
 ```