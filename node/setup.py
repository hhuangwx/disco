#!/usr/bin/python

from setuptools import setup, find_packages

setup(name = "disconode",
      version = "0.1",
      scripts = ["disco_worker"],
      packages = find_packages())
