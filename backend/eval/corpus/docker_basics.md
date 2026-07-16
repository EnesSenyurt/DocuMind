# Docker Basics

## Images versus Containers

A Docker image is an immutable, read-only template that bundles an application
together with its dependencies and configuration. A container is a running
instance of an image: it adds a thin writable layer on top of the image's layers.
You can start many containers from the same image, and each one is isolated from
the others.

## Writing a Dockerfile

A Dockerfile is a text file of instructions that describes how to build an image.
It starts from a base image with FROM, copies source code with COPY, installs
dependencies with RUN, and declares the startup command with CMD. Ordering the
instructions from least to most frequently changing maximizes layer cache reuse
and keeps rebuilds fast.

## Volumes

Containers are ephemeral, so data written inside them is lost when they are
removed. Volumes persist data outside the container's writable layer and can be
shared between containers, which is how databases keep their state across
restarts.
