""" Version of script as a represented as tuple """

version = (1, 1, 1)

# Version represented as string
version_str = ".".join([str(x) for x in version])

version_major = version[:1]
version_minor = version[:2]
version_full = version

version_major_str = ".".join([str(x) for x in version_major])
version_minor_str = ".".join([str(x) for x in version_minor])
version_full_str = ".".join([str(x) for x in version_full])
