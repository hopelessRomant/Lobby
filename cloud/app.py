#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cloud.cloud_stack import CloudStack


app = cdk.App()
CloudStack(app, "CloudStack",
    
    )

app.synth()
