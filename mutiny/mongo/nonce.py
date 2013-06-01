import uuid
import datetime


class Nonce:
    def __init__(self, **kwargs):
        if kwargs.get('uuid'):
            self.uuid = kwargs['uuid']
            self.expires = kwargs['expires']
        else:
            self.uuid = uuid.uuid4()
            self.expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=kwargs['expires'])

    def has_expired(self):
        return datetime.datetime.utcnow() > self.expires


class NonceManager:
    def __init__(self, collection, expiry=5, clear_stale=True):
        self.collection = collection
        self.expiry = expiry
        self.clear_stale = clear_stale
        self.last_cleared = datetime.datetime.utcnow()

    def generate(self):
        self._clear_check()
        nonce = Nonce(expires=self.expiry)
        self.collection.insert({"uuid": nonce.uuid, "expires": nonce.expires}, safe=True)
        return nonce

    def consume(self, id):
        '''Return true if consumed, false is not found or expired'''
        self._clear_check()
        try:
            id = uuid.UUID(id)
        except:
            logger.debug("%s is invalid" % id)
            return False

        data = self.collection.find_one({"uuid": id})
        if data is None:
            logger.debug("%r not found" % id)
            return False

        nonce = Nonce(**data)
        self.collection.remove(data)
        logger.debug("Expired: %s" % nonce.has_expired())
        return not nonce.has_expired()

    def clear_expired(self):
        expired = datetime.datetime.utcnow() + datetime.timedelta(minutes=self.expiry)
        self.collection.remove({"expires": {"$lt": expired}})

    def _clear_check(self):
        if not self.clear_stale:
            return

        if self.last_cleared + datetime.timedelta(hours=1) < datetime.datetime.utcnow():
            self.clear_expired()
            self.last_cleared = datetime.datetime.utcnow()
