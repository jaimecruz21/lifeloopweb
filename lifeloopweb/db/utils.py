import uuid
from lifeloopweb import exception

MAX_SHARD = 4096


def to_snake_case(name):
    chars = []
    first_char = True
    last_caps = False
    for c in name:
        if c.isupper():
            if first_char:
                first_char = False
                last_caps = True
            else:
                if not last_caps:
                    chars.append('_')
                last_caps = True
        else:
            last_caps = False
        chars.append(c.lower())
    return ''.join(chars)


def pluralize(name):
    if name.endswith('y'):
        return "{}ies".format(name[0:-1])
    elif name.endswith('s'):
        return "{}es".format(name)
    return "{}s".format(name)

# TODO relationship handler that can walk the meta and link to the correct
#      name without being overly "magical". Something like:
#      utils.relationship("User", pk_column_for) -> "users.id"
#      pk_column_for is a callable that figures out the PK for the model
#      could also be a string argument for the actual column name


def generate_guid(shard=0, base_uuid=None):
    """
    Generates an "optimized" UUID that accomodates the btree indexing
    algorithms used in database index b-trees. Check the internet for
    details but the tl;dr is big endian is everything.

    Leveraging the following as the reference implementation:
    https://www.percona.com/blog/2014/12/19/store-uuid-optimized-way/
    http://stackoverflow.com/questions/412341/how-should-i-store-guid-in-mysql-tables#27845470
    https://engineering.instagram.com/sharding-ids-at-instagram-1cf5a71e5a5c

    It works as follows, by reorganizing the most significant bytes of the
    timestamp portion of a UUID1 to ensure that UUIDs generated in close
    succession all land on the same (or at least adjacent) index pages.

    The implementation is provided in pure-python to ensure we aren't
    delegating the calculation to the SPOF that is our database. While not
    the most performant place to put this, it's by far the most flexible.

    12345678-9ABC-DEFG-HIJK-LMNOPQRSTUVW
    12345678 = least significant 4 bytes of the timestamp in big endian order
    9ABC     = middle 2 timestamp bytes in big endian
    D        = 1 to signify a version 1 UUID
    EFG      = most significant 12 bits of the timestamp in big endian
    When you convert to binary, the best order for indexing would be:
    EFG9ABC12345678D + the rest.

    Lastly, rather than implementing this as a type, through experimentation it
    was determined that the re-ordered UUID can be coerced back into the uuid
    type with no problems. This lets us rely on an existing implementation
    for UUIDs and instead only worry about supplying one. The alternative
    would be to implement in the type a conversion back to an "unordered" UUID
    when retrieving the column from the database, which would be wasted effort

    The last 12 bits of the UUID generated will be replaced with a shard id. By
    default we're allowing for 4096 shards, which is overkill for everyone but
    Facebook. However, it's easy to work with since every character in the
    UUID represents 4 bits, so all we have to do is overwrite 3 characters.
    """

    base_uuid = base_uuid or str(uuid.uuid1())
    if shard > MAX_SHARD:
        raise exception.InvalidShardId(shard_id=shard, max_shard=MAX_SHARD)

    shard_id = "{:03X}".format(shard)
    return uuid.UUID(''.join([base_uuid[15:18],
                              base_uuid[9],
                              base_uuid[10:13],
                              base_uuid[:8],
                              base_uuid[14],
                              base_uuid[19:23],
                              base_uuid[24:33],
                              shard_id]))
