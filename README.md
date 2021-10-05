## TRAGEN

TRAGEN is open-source software (tool) that generates synthetic request sequences that mimic the caching behavior of production request traces from Akamai. TRAGEN comes equipped with footprint descriptors (FDs) obtained for various traffic classes such as video, web, downloads, etc. that model the caching behavior of the traffic class. For a given user-specified traffic mix, TRAGEN uses the footprint descriptor calculus to compute the FD that is representative of the traffic mix and then generates a request sequence from it. The code used to compute the FDs is also made available for public use.
