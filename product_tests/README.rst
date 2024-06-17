UCS@school ID Connector Product Tests
=====================================

The product tests in this folder are executed on the host where the ID Connector is installed:

```bash
curl --output product_tests.tar.gz -L https://git.knut.univention.de/api/v4/projects/191/packages/generic/product_tests/0.0.1/product_tests.tar.gz
tar -xf product_tests.tar.gz
python3 -m pytest product_tests
```
