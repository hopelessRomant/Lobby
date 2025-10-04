#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { InfraStack } from '../lib/stack.ts';

const app = new cdk.App();

new InfraStack(app, 'InfraStack', {
});
