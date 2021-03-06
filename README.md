# Example API Server on GCP via Cloud Endpoints and App Engine

This is a very simple example API server using analagous technologies to the [data-store](https://github.com/HumanCellAtlas/data-store),
such as connexion, flask, open API v2, etc.

## Useful links:
Information about [Google Cloud Endpoints](https://cloud.google.com/endpoints/docs/openapi/get-started-app-engine#python)

Notes from building a REST API on top of Google Cloud Functions (GCF). Note that GCFs cannot integrate with Endpoints, making
this scheme considerably less attractive. We may look into calling GCFs from App Engine
[REST API on top of Google Cloud Functions](https://medium.com/@andyhume/building-a-rest-api-with-google-cloud-functions-e0acdf1b2620)

Notes on [pulling in external python modules](https://groups.google.com/forum/#!topic/google-appengine/e21mD63LCrs)

## Deploying
This will deploy a Google App Engine backed API fronted by Cloud Endpoints.

Do this once (it's already been done):
`make create`

Deploy changes with (from the repo root):
`make deploy`
