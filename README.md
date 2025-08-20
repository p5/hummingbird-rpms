# RHEL Primitives RPMs

This project hosts and builds all the RPM components required to build the container images in [gitlab.com/redhat/rhel-primitives/containers](https://gitlab.com/redhat/rhel-primitives/containers).

## Overview

This is a mono repository that contains:
- Spec files for all RPM components
- Package definitions for RPM components
- Build configurations and automation

## Goals

The primary goal is to establish a fully automated process for:
- Building RPM packages
- Managing package dependencies
- Updating packages automatically
- Providing reliable RPM components for container image builds

## Structure

All spec files and package definitions are organized within this mono repository to facilitate centralized management and automated builds.
