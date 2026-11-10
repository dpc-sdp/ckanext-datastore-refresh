# ckanext-datastore-refresh

:arrows_clockwise: :clock9:

This extension provides a option to refresh/reupload the datastore data when resource is uploaded by URL. Because there is no mechanism within CKAN core to track the changes in the files after the upload, we need to create cronjob that would call the CLI command to refresh data defined by the configuration panel as CKAN sysadmin.


## Requirements

Works with CKAN 2.9.x and above(python v3.7 and above).

Depends on [ckanext-datapusher-plus](https://github.com/dathere/datapusher-plus)

Compatibility with core CKAN versions:

| CKAN version | Compatible? |
|--------------|-------------|
| 2.9          | yes         |
| 2.10         | yes         |


## Installation

To install ckanext-datastore-refresh:

1. Clone the source and install it on the virtualenv

    ```sh
    git clone https://github.com/salsadigitalauorg/ckanext-datastore-refresh.git
    cd ckanext-datastore-refresh
    pip install -e .
    ```
1. Add `datastore_refresh` to the `ckan.plugins` setting in your CKAN
   config file.

1. Apply DB migrations:
   ```sh
   ckan db upgrade -p datastore_refresh
   ```

## Configuration

Configuration is done by the CKAN admin menu

```
@hourly ckan -c /path/to/ckan.ini datastore-refresh refresh_dataset_datastore 10
```
10 - frequency  to refresh the datastore  (in minutes)
Cron jobs can be set by the desired frequency which currently is set to 10 min, 2 hours or 24 hours

#TODO: Make frequencies configurable via ckan.ini file

### CDN purge

After each DataPusher+ load the extension can purge the cached `datastore_search` responses for the resource
(`/api/action/datastore_search?id=<id>` and `/api/3/action/datastore_search?id=<id>`), one request per path.
`{path}` in the URL, header values or body is replaced with that path. An empty URL disables purging.
Values pass through ini interpolation, so a `%` in a token must be written as `%%`.
When using `cdn_purge_body`, set `Content-Type` in `cdn_purge_headers`.

```ini
ckanext.datastore_refresh.cdn_purge_url = https://api.quantcdn.io/v1/purge
ckanext.datastore_refresh.cdn_purge_method = POST
ckanext.datastore_refresh.cdn_purge_headers = {"Quant-Token": "...", "Quant-Customer": "...", "Quant-Project": "...", "Quant-Url": "{path}"}
ckanext.datastore_refresh.cdn_purge_body =
```

## Tests

To run the tests, do:
```sh
pytest
```

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
