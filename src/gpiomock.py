class LED(object):
    def __init__(self, pin):
        self.pin = pin
    
    def on(self):
        print(f"ON : {self.pin}")

    def off(self):
        print(f"OFF: {self.pin}")
