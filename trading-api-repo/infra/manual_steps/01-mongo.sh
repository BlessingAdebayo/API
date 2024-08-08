
# Connect to the mongo cluster using the admin credentials (found in the AWS secrets manager) via one of the API nodes.
# Then create an api user in the mongodb shell for the trading api: (fill in a password!)
db.createUser(
{
  user: "apiuser",
  pwd: "",
  roles: [
    { role: "readWrite", db: "trading_api" },
  ],
}
)
