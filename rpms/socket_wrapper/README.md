socket_wrapper
==============
It is a library passing all socket communications through unix sockets.

Features
--------
socket_wrapper aims to help client/server software development teams willing to
gain full functional test coverage. It makes possible to run several instances
of the full software stack on the same machine and perform locally functional
testing of complex network configurations.

* Redirects all network communication to happen over unix sockets.
* Support for IPv4 and IPv6 socket and addressing emulation.
* Ablility to capture network traffic in pcap format.

Documentation
-------------
See [manual page](https://gitlab.com/cwrap/socket_wrapper/-/blob/master/doc/socket_wrapper.1.adoc) of socket_wrapper for details.

Installation
------------
Instructions to build and install can be found in [README.install](https://gitlab.com/cwrap/socket_wrapper/-/blob/master/README.install) file.

Development
-----------
Contributions to socket_wrapper in the form of patches can be made via official
GitLab mirror as [merge requests](https://gitlab.com/cwrap/socket_wrapper/-/merge_requests). It is backed by CI/CD pipelines.

License
-------
BSD 3-Clause License.

Please visit [cwrap web page](https://cwrap.org/socket_wrapper.html) to find out more about socket_wrapper.
