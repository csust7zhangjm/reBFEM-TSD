import math
import os

import torch
import torch.nn as nn
from torch.hub import load_state_dict_from_url
import thop
from thop import profile

class Bottleneck(nn.Module):
    # ResNet-B
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride,
                               padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * Bottleneck.expansion, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * Bottleneck.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out

class ResNet(nn.Module):

    def __init__(self, block, layers, num_classes=1000, if_include_top=False):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1      = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)  #7*7 conv
        self.bn1        = nn.BatchNorm2d(64)
        self.relu       = nn.ReLU(inplace=True)
        self.maxpool    = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1     = self._make_layer(block, 64, layers[0])
        self.layer2     = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3     = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4     = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool    = nn.AvgPool2d(7, stride=1)

        if if_include_top:
            self.fc = nn.Linear(512 * block.expansion, num_classes)
        self.if_include_top=if_include_top

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        out3 = self.layer2(x)
        out4 = self.layer3(out3)
        out5 = self.layer4(out4)

        if self.if_include_top:
            x = self.avgpool(out5)
            x = x.view(x.size(0), -1)
            x = self.fc(x)
            return x
        else:
            return (out3, out4, out5)

def resnet50(pretrained):
    model = ResNet(Bottleneck, [2, 2, 2, 2])
    if pretrained:
        pth_path = os.path.join('model_data', 'resnet18.pth')
        model.load_state_dict(torch.load(pth_path), strict=False)
    return model


# if __name__ == '__main__':
#     model = ResNet(Bottleneck, [2, 2, 2, 2])
#     x = torch.randn([1, 3, 608, 608])
#     out = model(x)
#     for o in out:
#         print(o.shape)
#     print(model)
#     # 计算FLOPS
#     flops, params = profile(model, inputs=(x, ))
#     print(flops / 1e9, params / 1e6)  # flops单位G，para单位M
#     # 18.06 11.88


# torch.Size([1, 512, 76, 76])
# torch.Size([1, 1024, 38, 38])
# torch.Size([1, 2048, 19, 19])
