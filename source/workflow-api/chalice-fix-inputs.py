#!/usr/bin/python

# # Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from pprint import pprint

def fix_chalice_sam_template():
    
    sam_json = json.load(open('./dist/sam.json'))
    # pprint(sam_json)

    #stack_inputs_json = json.load(open('./chalice-stack-inputs.json'))
    #pprint(stack_inputs_json)

    sam_json["Parameters"] = {
        "WorkflowTableName": {
                "Type": "String",
                "Description": "Table used to store workflow defintitions" 
                },
        "StageTableName": {
                "Type": "String",
                "Description": "Table used to store stage definitions" 
                },
        "WorkflowExecutionTableName": {
                "Type": "String",
                "Description": "Table used to monitor Workflow executions" 
                },
        "StageExecutionQueueUrl": {
                "Type": "String",
                "Description": "Queue used to post stage executions for processing" 
                },
        "StageExecutionRole": {
                "Type": "String",
                "Description": "ARN of the role used to execute a stage state machine" 
                },
        "OperationTableName": {
                "Type": "String",
                "Description": "Table used to store operations" 
                },
        "CompleteStageLambdaArn": {
                "Type": "String",
                "Description": "Lambda that completes execution of a stage" 
                },
        "DataPlaneAPIEndpoint": {
            "Type": "String",
            "Description": "Rest endpoint for the dataplane"
        },
        "DataPlaneBucket": {
            "Type": "String",
            "Description": "S3 bucket of the dataplane"
        }
    }

    environment = {
        "Variables": {
                "WORKFLOW_TABLE_NAME": {
                        "Ref":"WorkflowTableName"
                },
                "WORKFLOW_EXECUTION_TABLE_NAME": {
                        "Ref":"WorkflowExecutionTableName"
                },
                "STAGE_TABLE_NAME": {
                        "Ref":"StageTableName"
                },
                "STAGE_EXECUTION_QUEUE_URL": {
                        "Ref":"StageExecutionQueueUrl"
                },
                "OPERATION_TABLE_NAME": {
                        "Ref":"OperationTableName"
                },
                "COMPLETE_STAGE_LAMBDA_ARN": {
                        "Ref":"CompleteStageLambdaArn"
                },
                "STAGE_EXECUTION_ROLE": {
                        "Ref":"StageExecutionRole"
                },
                "DATAPLANE_ENDPOINT": {
                    "Ref": "DataPlaneAPIEndpoint"
                },
                "DATAPLANE_BUCKET": {
                    "Ref": "DataPlaneBucket"
                }
            }
        }

    
    # Replace environment variables for all the lambdas
    #pprint(MediainfoRuleEngine_environment_json)
    for resourceName, resource in sam_json["Resources"].iteritems():
        if (resource["Type"] == "AWS::Serverless::Function"):
            sam_json["Resources"][resourceName]["Properties"]["Environment"] = environment

    # add lambdas to stack outputs
    for resourceName, resource in sam_json["Resources"].iteritems():
        if (resource["Type"] == "AWS::Serverless::Function"):
            sam_json["Resources"][resourceName]["Properties"]["Environment"] = environment
        
            outputName = resourceName+"Arn"
            sam_json["Outputs"][outputName] = {"Value": {"Fn::GetAtt": [resourceName, "Arn" ] }}

    with open('./dist/sam.json', 'w') as outfile:
        json.dump(sam_json, outfile)


def main():
    fix_chalice_sam_template()


if __name__ == '__main__':
    main()