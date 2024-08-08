# Cloud Development Kit

## Introduction

The _Cloud Development Kit_ (CDK), automates the deployment of Mercor
infrastructure to AWS. This is achieved through interacting with a `npm`
package provided by Amazon using Python.

A short summary on how it works:
1. The code defines an `app`, which represents the `app` environment.
2. You create `stacks` in code, where a stack is a deployable unit.
3. When running `cdk deploy <stack>`, AWS compares the currently deployed
   version of the stack (referenced by an id) to the stack defined in the code,
   and consequently creates a change-set. Depending on whether there are any
   changes in the change-set, it will do something. The state is saved in
   `./cdk.out`.

## Installation

``` sh
$ sudo apt update
$ sudo apt install python3 python3-venv
$ sudo apt install nodejs npm
$ sudo apt install awscli
$ npm install -g aws-cdk
$ aws configure # leave output format blank
$ cdk bootstrap
$ python3 -m venv venv
$ source venv/bin/activate
$ python3 -m pip install -r requirements.txt
```

## Deployment

1. Go to the [AWS Certificate Manager][1] and request a public certificate.
2. At the end, make sure to download the DNS conf csv file. This file contains
   a name and a value.
3. Add the name and value as a CNAME record (through the DNS provider). Make
   sure to strip the base address from the path as it is already provided by
   the DNS provider (e.g. `dev.api.mercor.com` -> `dev.api`). AWS will verify
   the certificate.
4. Wait for verification (which can take up to 30 minutes).
5. Get the ARN value of the certificate and the domain name, and add them to
   `cdk.json`.
6. Run `cdk deploy trading-api-<env>`, where `<env>` is something like
   "development", "staging", or "production".
7. Go to the [EC2 Management Console][2] and register the DNS of the load
   balancer as a CNAME record with the DNS provider.

## Remote Access

Give the access-key file (as found in LastPass) the correct permissions:

``` sh
$ chmod 600 <keyfile.pem>
```

Start `ssh-agent` (if it is not already running):

``` sh
$ eval $(ssh-agent)
```

Add the private key to `ssh-agent`:

``` sh
$ ssh-add <keyfile.pem>
```

Optionally verify the above was successful:

``` sh
$ ssh-add -L
```

Connect to the private RSE node using the bastion host:

``` sh
ssh -A ubuntu@<bastion-public-ip>
ssh ubuntu@<node-private-ip>
```

(or in one command):

``` sh
$ ssh -J ubuntu@<bastion-public-ip> ubuntu@<node-private-ip>
```

## AWS CDK Toolkit Cheatsheet

``` sh
ckd diff
ckd diff <stack>  # e.g. `cdk diff trading-api-development`
cdk ls
cdk deploy <stack>
cdk destroy <stack>
```

## MongoDB User

After deploying the mongodb stack you need to configure a user your application
can use. Default MongoDB clusters only have a cluster admin user, which
cannot/should not be used for read/writes and applications.

Connect to a node that has internet access using `ssh` and follow these steps:

1. Download the Amazon DocumentDB Certificate Authority (CA) certificate
   required for authentication:
   `wget https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem`
2. Connect to the cluster using mongo shell. Replace `<host>` with the mongo
   host defined in [Amazon DocumentDB][3]:
   `mongo --ssl --host <host>:27017 --sslCAFile rds-combined-ca-bundle.pem --username masterdocdb --password`
3. Fill in the cluster admin user password as found in the [AWS Secrets
   Manager][4] when prompted.
4. Run the following script and fill in the password field (and save it in
   LastPass):
   ```
   db.createUser(
   {
     user: "apiuser",
     pwd: "",
     roles: [
       { role: "readWrite", db: "trading_api" },
     ],
   }
   )
   ```
5. Update the AWS secrets such that your app can connect with the user/password
   just created.

## PostgreSQL Database

After deploying the RSE, a database needs to be created for PostgreSQL
manually. Fill in the required values as found in the [AWS Secrets Manager][4]:

``` sh
$ psql --host=<SQL_HOST> --port=<SQL_PORT> --username=<SQL_USER> --password
postgres=> CREATE DATABASE <SQL_DB>;
```

## Trading API Redeployment Order

1. `vpc`
2. `redis`
3. `mongodb`
4. `trading_api`
5. MongoDB User (see above)
6. Deploy script

## Troubleshooting

If something goes wrong, go to [AWS CloudFormation][5] and check the _events_
of a stack for help with understanding the problem. You might have to delete
some things by hand and start over.

## Resources

- https://bobbyhadz.com/blog/aws-cdk-ec2-instance-example
- https://bobbyhadz.com/blog/aws-cdk-security-group-example
- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-update-certificates.html
- https://garbe.io/blog/2020/05/27/hey-cdk-how-to-oidc-alb-fargate/
- https://github.com/aws-samples/aws-cdk-examples/tree/master/python

[1]: https://eu-west-1.console.aws.amazon.com/acm/home?region=eu-west-1#/certificates/request
[2]: https://eu-west-1.console.aws.amazon.com/ec2/v2/home?region=eu-west-1#LoadBalancers
[3]: https://eu-west-1.console.aws.amazon.com/docdb/home?region=eu-west-1#clusters
[4]: https://eu-west-1.console.aws.amazon.com/secretsmanager/home?region=eu-west-1#!/listSecrets
[5]: https://eu-west-1.console.aws.amazon.com/cloudformation/home?region=eu-west-1#/stacks
