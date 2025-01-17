from setuptools import find_packages, setup

setup(
    name="docs_beta_snippets",
    author="Dagster Labs",
    author_email="hello@dagsterlabs.com",
    license="Apache-2.0",
    url="https://github.com/dagster-io/dagster/tree/master/examples/docs_beta_snippets",
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(exclude=["test"]),
    install_requires=["dagster-cloud", "dagster-aws"],
    extras_require={"test": ["pytest", "mock", "path", "dagster_snowflake"]},
)
