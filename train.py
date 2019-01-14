import numpy as np
import torch
from torch import nn
from torch import optim
import matplotlib.pyplot as plt
from torchvision import datasets, transforms, models
import torch.nn.functional as F
from collections import OrderedDict
import json
from torch.autograd import Variable
import argparse
import os


def args_paser():
    paser = argparse.ArgumentParser(description='trainer file')

    paser.add_argument('--data_dir', type=str, default='flowers', help='dataset directory')
    paser.add_argument('--gpu', type=bool, default='True', help='True: gpu, False: cpu')
    paser.add_argument('--lr', type=float, default=0.001, help='learning rate')
    paser.add_argument('--epochs', type=int, default=10, help='num of epochs')
    paser.add_argument('--arch', type=str, default='vgg16', help='architecture')
    paser.add_argument('--hidden_units', type=int, default=[600, 200], help='hidden units for layer')
    paser.add_argument('--save_dir', type=str, default='checkpoint.pth', help='save train model to a file')

    args = paser.parse_args()
    return args


def process_data(train_dir, test_dir, valid_dir):
    train_transforms = transforms.Compose([transforms.RandomRotation(30),
                                           transforms.RandomResizedCrop(224),
                                           transforms.RandomHorizontalFlip(),
                                           transforms.ToTensor(),
                                           transforms.Normalize([0.485, 0.456, 0.406],
                                                                [0.229, 0.224, 0.225])])

    test_transforms = transforms.Compose([transforms.Resize(255),
                                          transforms.CenterCrop(224),
                                          transforms.ToTensor(),
                                          transforms.Normalize([0.485, 0.456, 0.406],
                                                               [0.229, 0.224, 0.225])])

    valid_transforms = transforms.Compose([transforms.Resize(255),
                                           transforms.CenterCrop(224),
                                           transforms.ToTensor(),
                                           transforms.Normalize([0.485, 0.456, 0.406],
                                                                [0.229, 0.224, 0.225])])

    train_datasets = datasets.ImageFolder(train_dir, transform=train_transforms)
    test_datasets = datasets.ImageFolder(test_dir, transform=test_transforms)
    valid_datasets = datasets.ImageFolder(valid_dir, transform=valid_transforms)

    trainloaders = torch.utils.data.DataLoader(train_datasets, batch_size=64, shuffle=True)
    testloaders = torch.utils.data.DataLoader(test_datasets, batch_size=64, shuffle=True)
    validloaders = torch.utils.data.DataLoader(valid_datasets, batch_size=64, shuffle=True)

    return trainloaders, testloaders, validloaders


def basic_model(arch):
    # Load pretrained_network
    if arch == None:
        load_model = models.vgg16(pretrained=True)
        # load_model.name = 'vgg16'
        print('Use vgg16')
    else:
        print('Please vgg16 or desnent only, defaulting to vgg16')
        load_model = models.vgg16(pretrained=True)

    for param in load_model.parameters():
        param.requires_grad = False

    return load_model


def set_classifier(load_model, hidden_units):
    if hidden_units == None:
        hidden_units = 512

    input = load_model.classifier[0].in_features
    classifier = nn.Sequential(OrderedDict([('fc1', nn.Linear(input, hidden_units, bias=True)),
                                                  ('relu1', nn.ReLU()),
                                                  ('dropout', nn.Dropout(p=0.5)),
                                                  ('fc2', nn.Linear(hidden_units, 128, bias=True)),
                                                  ('relu2', nn.ReLU()),
                                                  ('dropout', nn.Dropout(p=0.5)),
                                                  ('fc3', nn.Linear(128, 102, bias=True)),
                                                  ('output', nn.LogSoftmax(dim=1))
                                                  ]))

    #load_model.classifier = classifier

    return classifier

    print(f"Epoch {epoch+1}/{epochs}.. "
          f"Train loss: {running_loss/print_every:.3f}.. ")


def train_model(epochs, trainloaders, validloaders, gpu, Model, optimizer, criterion):
    if type(epochs) == type(None):
        epochs = 10
        print("Epochs = 10")
    steps = 0

    #Model.to('cuda')

    print_every = 60

    for epoch in range(epochs):
        running_loss = 0
        Model.train()
        for inputs, labels in trainloaders:
            steps += 1
            if gpu == True:
                inputs, labels = inputs.to('cuda'), labels.to('cuda')

            optimizer.zero_grad()

            logps = model.forward(inputs)
            loss = criterion(logps, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

            if steps % print_every == 0:
                test_loss = 0
                accuracy = 0
                model.eval()
                with torch.no_grad():
                    for inputs, labels in validloaders:
                        inputs, labels = inputs.to('cuda'), labels.to('cuda')
                        logps = model.forward(inputs)
                        batch_loss = criterion(logps, labels)
                        test_loss += batch_loss.item()

                        # Calculate accuracy
                        ps = torch.exp(logps)
                        top_p, top_class = ps.topk(1, dim=1)
                        equals = top_class == labels.view(*top_class.shape)
                        accuracy += torch.mean(equals.type(torch.FloatTensor)).item()

                        print(f"Epoch {epoch+1}/{epochs}.. "
                              f"Train loss: {running_loss/print_every:.3f}.. "
                              f"Valid loss: {test_loss/len(validloaders):.3f}.."
                              f"Valid accuracy: {accuracy/len(validloaders):.3f}")
                    running_loss = 0
                model.train()

    return Model


def valid_model(Model, testloaders, gpu):
    test_loss = 0
    accuracy = 0
    Model.eval()
    with torch.no_grad():
        for inputs, labels in testloaders:
            if gpu == True:
                inputs, labels = inputs.to('cuda'), labels.to('cuda')
            logps = Model.forward(inputs)
            batch_loss = criterion(logps, labels)

            test_loss += batch_loss.item()

            # Calculate accuracy
            ps = torch.exp(logps)
            top_p, top_class = ps.topk(1, dim=1)
            equals = top_class == labels.view(*top_class.shape)
            accuracy += torch.mean(equals.type(torch.FloatTensor)).item()

    print(f"Valid loss: {test_loss/len(testloaders):.3f}.."
          f"Valid accuracy: {accuracy/len(testloaders):.3f}")


def save_checkpoint(Model, train_datasets, save_dir):
    Model.class_to_idx = train_datasets.class_to_idx

    checkpoint = {'structure': Model.name,
                  'classifier': Model.classifier,
                  'state_dic': Model.state_dict(),
                  'class_to_idx': Model.class_to_idx}

    return torch.save(checkpoint, save_dir)


def main():
    args = args_paser()

    data_dir = 'flowers'
    train_dir = data_dir + '/train'
    valid_dir = data_dir + '/valid'
    test_dir = data_dir + '/test'

    trainloaders, testloaders, validloaders = process_data(train_dir, test_dir, valid_dir)
    model = basic_model(args.arch)


    model = set_classifier(model, args.hidden_units)

    criterion = nn.NLLLoss()
    optimizer = optim.Adam(model.classifier.parameters(), lr=args.lr)
    trmodel = train_model(args.epochs, trainloaders, validloaders, args.gpu, model, optimizer, criterion)
    print('Completed!')

    valid_model(trmodel, testloaders, args.gpu)
    save_checkpoint(trmodel, train_datasets, args.save_dir)



if __name__ == '__main__': main()
