#!/usr/bin/env python
# -*- coding: utf-8 -*-

import vcversioner

version = release = vcversioner.find_version(root='.').version
