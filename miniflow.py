import numpy as np

## Node
class Node(object):
    def __init__(self, inbound_nodes=[], name=None):
        self.inbound_nodes = inbound_nodes  # Node(s) from which this Node receives values
        self.outbound_nodes = []   # Node(s) to which this Node passes values
        self.gradients = {}
        self.name = name
        # For each inbound Node here, add this Node as an outbound Node to _that_ Node.
        for n in self.inbound_nodes:
            n.outbound_nodes.append(self)
        self.value = None  # A calculated value

    # Placeholder
    def forward(self):
        # Compute output value based on 'inbound_nodes' and store the result in self.value.
        raise NotImplemented  # Subclasses must implement this function to avoid errors.

    # Placeholder
    def backward(self):
        raise NotImplemented  # Subclasses must implement this function to avoid errors.


class Input(Node):
    def __init__(self, name=None):
        Node.__init__(self, name=name)

    def forward(self, value=None):
        pass
    
    def backward(self):
        self.gradients = {self: 0}
        for n in self.outbound_nodes:
            grad_cost = n.gradients[self]
            self.gradients[self] += grad_cost * 1


class Linear(Node):
    def __init__(self, X, W, b, name=None):
        Node.__init__(self, [X, W, b], name=name)

    def forward(self):
        XX = self.inbound_nodes[0].value
        WW = self.inbound_nodes[1].value
        bb = self.inbound_nodes[2].value
        self.value = np.dot(XX,WW) + bb        

    def backward(self):
        self.gradients = {n: np.zeros_like(n.value) for n in self.inbound_nodes}  # Initialize to 0
        for n in self.outbound_nodes:
            grad_cost = n.gradients[self]
            self.gradients[self.inbound_nodes[0]] += np.dot(grad_cost, self.inbound_nodes[1].value.T)  # dL/dX = dL/dY \dot W_T
            self.gradients[self.inbound_nodes[1]] += np.dot(self.inbound_nodes[0].value.T, grad_cost)  # dL/dW = X_T \dot dL/dY
            self.gradients[self.inbound_nodes[2]] += np.sum(grad_cost, axis=0, keepdims=False)  # dL / db = 1


## Activation function
class Sigmoid(Node):
    def __init__(self, node, name=None):
        Node.__init__(self, [node], name=name)
    
    def _sigmoid(self, x):
        return 1./(1.+np.exp(-x))

    def forward(self):
        self.value = self._sigmoid(self.inbound_nodes[0].value)  # S = 1 / ( 1 + e**(-x))

    def backward(self):
        self.gradients = {n: np.zeros_like(n.value) for n in self.inbound_nodes}  # Initialize to 0 
        for n in self.outbound_nodes:
            grad_cost = n.gradients[self]
            self.gradients[self.inbound_nodes[0]] += grad_cost*self.value*(1-self.value)  # (dC / dS) * (dS / dL)


class Relu(Node):
    def __init__(self, node, name=None):
        Node.__init__(self, [node], name=name)
    
    def forward(self):
        self.value = self.inbound_nodes[0].value.copy()
        self.value[self.value<0] = 0.

    def backward(self):
        self.gradients = {n: np.zeros_like(n.value) for n in self.inbound_nodes}  # Initialize to 0 
        for n in self.outbound_nodes:
            grad_cost = n.gradients[self]
            grad_value = self.value.copy()
            grad_value[grad_value>0] = 1 
            self.gradients[self.inbound_nodes[0]] += grad_cost * grad_value


## Loss function
class MSE(Node):
    def __init__(self, y, a, name=None):
        Node.__init__(self, [y, a], name=name)

    def forward(self):
        y = self.inbound_nodes[0].value.reshape(-1,1)
        a = self.inbound_nodes[1].value.reshape(-1,1)
        self.m = len(y)
        self.error = y-a
        self.value = np.sum(np.square(self.error))/self.m  # C = SIGMA((y-a)**2) / m

    def backward(self):
        self.gradients[self.inbound_nodes[0]] = (2/self.m)*self.error  # dC / dy  
        self.gradients[self.inbound_nodes[1]] = (-2/self.m)*self.error # dC / da


class SoftmaxCrossEntropy(Node):
    def __init__(self, y, a, name=None):
        Node.__init__(self, [y, a], name=name)

    def _softmax(self, x):
        return np.exp(x) / np.sum(np.exp(x), axis=1, keepdims=True)

    def forward(self):
        self.y = self.inbound_nodes[0].value
        self.a = self._softmax(self.inbound_nodes[1].value)

        # If one hot encoding, change max value index
        if self.y.shape[1] == self.a.shape[1]:
            self.y = self.y.argmax(axis=1) 

        self.m = self.y.shape[0]
        correct_logprobs = -np.log(self.a[np.arange(self.y.shape[0]), self.y])
        self.value = np.sum(correct_logprobs) / self.m

    def backward(self):
        da = self.a.copy()
        da[np.arange(self.y.shape[0]), self.y] -= 1
        self.gradients[self.inbound_nodes[0]] = -np.sum(np.log(self.a), axis=1)
        self.gradients[self.inbound_nodes[1]] = da / self.m


## Create graph
def topological_sort(feed_dict):
    input_nodes = [ n for n in feed_dict.keys() ]

    G = {}
    G_name = {}
    nodes = [ n for n in input_nodes ]
    while len(nodes) > 0:
        n = nodes.pop(0)
        if n not in G:
            G[n] = { 'in': set(), 'out': set() }
            G_name[n.name] = { 'in': set(), 'out': set() }
        for m in n.outbound_nodes:
            if m not in G:
                G[m] = { 'in': set(), 'out': set() }
                G_name[m.name] = { 'in': set(), 'out': set() }
            G[n]['out'].add(m)
            G[m]['in'].add(n)
            G_name[n.name]['out'].add(m.name)
            G_name[m.name]['in'].add(n.name)
            nodes.append(m)

    L = []
    S = set(input_nodes)
    while len(S) > 0:
        n = S.pop()
        if isinstance(n, Input):
            n.value = feed_dict[n]
        L.append(n)
        for m in n.outbound_nodes:
            G[n]['out'].remove(m)
            G[m]['in'].remove(n)
            if len(G[m]['in']) == 0:
                S.add(m)
    return L

def forward_and_backward(graph, training=True):
    for n in graph:
        n.forward()

    if training:
        for n in graph[::-1]:  # Extended slice - reverse order
            n.backward()


## Optimizer
class Optimizer(object):
    def __init__(self, trainables = [], learning_rate=0.001):
        self.trainables = trainables
        self.learning_rate = learning_rate

    def update(self):
        raise NotImplemented  # Subclasses must implement this function to avoid errors.


class SGD(Optimizer):
    def __init__(self, trainables, learning_rate):
        Optimizer.__init__(self, trainables, learning_rate)

    def update(self):
        for t in self.trainables:
            t.value -= self.learning_rate * t.gradients[t]


class Momentum(Optimizer):
    def __init__(self, trainables, learning_rate, momentum=0.9):
        Optimizer.__init__(self, trainables, learning_rate)
        self.momentum = momentum
        self.v = {}

    def update(self):
        for t in self.trainables:
            if t not in self.v:
                self.v[t] = np.zeros_like(t.value)
            self.v[t] = self.momentum * self.v[t] - self.learning_rate * t.gradients[t]
            t.value += self.v[t]


class Adagrad(Optimizer):
    def __init__(self, trainables, learning_rate, eps=1e-8):
        Optimizer.__init__(self, trainables, learning_rate)
        self.eps = eps
        self.h = {}

    def update(self):
        for t in self.trainables:
            if t not in self.h:
                self.h[t] = np.zeros_like(t.value)
            self.h[t] += t.gradients[t] * t.gradients[t]
            t.value -= self.learning_rate * t.gradients[t] / (np.sqrt(self.h[t]) + self.eps) 

class RMSProp(Optimizer):
    def __init__(self, trainables, learning_rate, decay_rate=0.99, eps=1e-8):
        Optimizer.__init__(self, trainables, learning_rate)
        self.decay_rate = decay_rate
        self.eps = eps
        self.h = {}

    def update(self):
        for t in self.trainables:
            if t not in self.h:
                self.h[t] = np.zeros_like(t.value)
            self.h[t] = self.decay_rate * self.h[t] + (1 - self.decay_rate) *  t.gradients[t] * t.gradients[t]
            t.value -= self.learning_rate * t.gradients[t] / (np.sqrt(self.h[t]) + self.eps) 
        

class Adam(Optimizer):
    def __init__(self, trainables, learning_rate, beta1=0.9, beta2=0.999, eps=1e-8):
        Optimizer.__init__(self, trainables, learning_rate)
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.t = 0
        self.m = {}
        self.v = {}

    def update(self):
        self.t += 1
        for t in self.trainables:
            if t not in self.m:
                self.m[t] = np.zeros_like(t.value)
                self.v[t] = np.zeros_like(t.value)

            self.m[t] = self.beta1 * self.m[t] + (1 - self.beta1) *  t.gradients[t]
            self.v[t] = self.beta2 * self.v[t] + (1 - self.beta2) *  t.gradients[t] * t.gradients[t]
            m_t = self.m[t] / (1 - self.beta1**self.t) # unbiased m
            v_t = self.v[t] / (1 - self.beta2**self.t) # unbiased v
            t.value -= self.learning_rate * m_t / np.sqrt(v_t + self.eps)

