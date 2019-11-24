# Generate OSM Borders

The **generate-osmborder** Docker container will take the first PBF file and generate the CSV file.

## Usage

* Download PBF File

Use [Geofabrik](http://download.geofabrik.de/index.html) and choose the extract
of your country or region. Download it and put it into the directory.

* Generate

Mount your PBFs into the `/import` folder


```bash
docker run --rm \
    -v $(pwd):/import \
    openmaptiles/generate-osmborder
```

Now upload the generated CSV to GitHub releases and update the reference link inside **import-osmborder**.
