import * as path from 'path';
import * as cdk from 'aws-cdk-lib';


export class InfraStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
  }
}