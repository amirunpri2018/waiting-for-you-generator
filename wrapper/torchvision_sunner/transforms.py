from torch.autograd import Variable
import torchvision.transforms.functional as F
import numpy as np
import torch

BCHW2BHWC = 0
BHWC2BCHW = 1

class Rescale(object):
    def __init__(self, output_size, use_cv = True):
        assert isinstance(output_size, (int, tuple))
        self.output_size = output_size
        self.use_cv = use_cv

        # -------------------------------------------------------
        # Reverse the order 
        # cv2       order: [width, height]
        # pytorch   order: [hdight, width]
        # -------------------------------------------------------
        if self.use_cv:
            if len(self.output_size) == 2:
                self.output_size = tuple(reversed(list(self.output_size)))
        print("[ Transform ] - Applied << %15s >>, you should notice the rank format is 'BHWC'" % self.__class__.__name__)

    def __call__(self, sample):
        if self.use_cv:
            import cv2
            return cv2.resize(sample, self.output_size)
        else:
            from skimage import transform
            sample = transform.resize(sample, self.output_size)
            sample *= 255
            return sample            

class ToTensor(object):
    def __init__(self):
        print("[ Transform ] - Applied << %15s >>" % self.__class__.__name__)

    def __call__(self, sample):
        # Deal with gray-scale image
        if len(np.shape(sample)) == 2:
            sample = sample[:, :, np.newaxis]
            sample = np.tile(sample, 3)
        return torch.from_numpy(sample)

class ToFloat(object):
    def __init__(self):
        print("[ Transform ] - Applied << %15s >>" % self.__class__.__name__)

    def __call__(self, sample):
        return sample.float()

class Transpose(object):
    def __init__(self, direction = BHWC2BCHW):
        self.direction = direction
        if self.direction == BHWC2BCHW:
            print("[ Transform ] - Applied << %15s >>, The rank format is BCHW" % self.__class__.__name__)
        elif self.direction == BCHW2BHWC:
            print("[ Transform ] - Applied << %15s >>, The rank format is BHWC" % self.__class__.__name__)
        else:
            raise Exception('Unknown direction symbol...')

    def __call__(self, sample):
        last_dim = len(sample.size())
        if self.direction == BHWC2BCHW:
            return sample.transpose(last_dim - 2, last_dim - 1).transpose(last_dim - 3, last_dim - 2)
        elif self.direction == BCHW2BHWC:
            return sample.transpose(last_dim - 3, last_dim - 2).transpose(last_dim - 2, last_dim - 1)
        else:
            raise Exception('Unknown direction symbol...')

class Normalize(object):
    """
        Normalize toward two tensor
    """
    def __init__(self, mean = None, std = None):
        """
            Normalize the tensor with given mean and standard deviation
            * Notice: If you didn't give mean and std, the result will locate in [-1, 1]
            Args:
                mean    - The mean of the result tensor
                std     - The standard deviation
        """
        self.mean = mean
        self.std = std
        if (mean is None and std is not None) or (mean is not None and std is None):
            raise Exception('You should assign mean and std at the same time! (Or not assign at the same time)')
        print("[ Transform ] - Applied << %15s >>, you should notice the rank format should be 'BCHW'" % self.__class__.__name__)
        if mean is None and std is None:
            print("[ Transform ] - You should notice that the result will locate in [-1, 1]")

    def __call__(self, sample):
        """
        Args:
            tensor (Tensor): Tensor image of size (C, H, W) to be normalized.
        Returns:
            Tensor: Normalized Tensor image.
        """
        sample = sample.float() if type(sample) == torch.ByteTensor else sample
        if self.mean is not None and self.std is not None:
            if len(sample.size()) == 3:
                sample = F.normalize(sample, self.mean, self.std)
            else:
                for t in sample:
                    t = F.normalize(t, self.mean, self.std)
        else:
            if len(sample.size()) == 3:
                sample = self.normalize_none(sample)
            else:
                for t in sample:
                    t = self.normalize_none(t)
        return sample

    def normalize_none(self, t):
        t = torch.div(t, 255)
        t = torch.mul(t, 2)
        t = torch.add(t, -1)
        return t

class UnNormalize(object):
    has_show_warn = False

    def __init__(self, mean = None, std = None):
        """
            Unnormalize the tensor with given mean and standard deviation
            * Notice: If you didn't give mean and std, the function will assume that the original distribution locates in [-1, 1]
            Args:
                mean    - The mean of the result tensor
                std     - The standard deviation
        """
        self.mean = mean
        self.std = std
        if (mean is None and std is not None) or (mean is not None and std is None):
            raise Exception('You should assign mean and std at the same time! (Or not assign at the same time)')
        if self.has_show_warn == False:
            print("[ Transform ] - Applied << %15s >>, you should notice the rank format should be 'BCHW'" % self.__class__.__name__)
            if mean is None and std is None:
                print("[ Transform ] - You should notice that the range of original distribution will be assumeed in [-1, 1]")
            self.has_show_warn = True

    def __call__(self, tensor):
        """
        Args:
            tensor (Tensor): Tensor image of size (C, H, W) to be normalized.
        Returns:
            Tensor: Normalized image.
        """
        def _unnormalize(_tensor, _mean, _std):
            _result = []
            for t, m, s in zip(_tensor, self.mean, self.std):
                t = torch.mul(t, s)
                t = t.add_(m)
                _result.append(t)
            _tensor = torch.stack(_result, 0)
            return _tensor

        tensor = tensor.float() if type(tensor) == torch.ByteTensor else tensor
        if self.mean is not None and self.std is not None:
            if len(tensor.size()) == 3:
                tensor = _unnormalize(tensor, self.mean, self.std)
            else:
                result = []
                for t in tensor:
                    t = _unnormalize(t, self.mean, self.std)
                    result.append(t)
                tensor = torch.stack(result, 0)
        else:
            if len(tensor.size()) == 3:
                tensor = self.unnormalize_none(tensor)
            else:
                result = []
                for t in tensor:
                    t = self.unnormalize_none(t)
                    result.append(t)
                tensor = torch.stack(result, 0)
        return tensor

    def unnormalize_none(self, tensor):
        _result = []
        for t in tensor:
            t = torch.add(t, 1)
            t = torch.div(t, 2)
            t = t.mul_(255)
            _result.append(t)
        return torch.stack(_result, 0)

def tensor2Numpy(tensor, transform = None):
    if type(tensor) == Variable:
        tensor = tensor.data
    tensor = tensor.cpu()
    if transform:
        tensor = transform(tensor)
    return tensor.numpy()