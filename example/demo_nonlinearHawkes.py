"""
An example of nonlinear Hawkes process model without features.
In this case, the parameters can be negative
If softplus is used, sparsity constraint should not be applied.
"""

import numpy as np
import torch
import torch.optim as optim
from torch.optim import lr_scheduler
from torch.utils.data import DataLoader
import dev.util as util
from model.HawkesProcess import HawkesProcessModel
from preprocess.DataIO import load_sequences_csv
from preprocess.DataOperation import data_info, EventSampler, enumerate_all_events

# hyper-parameters
memory_size = 10
batch_size = 128
use_cuda = False
use_cuda = use_cuda and torch.cuda.is_available()
seed = 1
torch.manual_seed(seed)
if use_cuda:
    torch.cuda.manual_seed(seed)
kwargs = {'num_workers': 1, 'pin_memory': True} if use_cuda else {}
epochs = 5

# test sequence loading functions
# load event sequences from csv file
domain_names = {'seq_id': 'id',
                'time': 'time',
                'event': 'event'}
database = load_sequences_csv('{}/{}/Linkedin.csv'.format(util.POPPY_PATH, util.DATA_DIR),
                              domain_names=domain_names)
data_info(database)

# sample batches from database
trainloader = DataLoader(EventSampler(database=database, memorysize=memory_size),
                         batch_size=batch_size,
                         shuffle=True,
                         **kwargs)
validloader = DataLoader(EventSampler(database=database, memorysize=memory_size),
                         batch_size=batch_size,
                         shuffle=True,
                         **kwargs)

# initialize model
num_type = len(database['type2idx'])
mu_dict = {'model_name': 'NaiveExogenousIntensity',
           'parameter_set': {'activation': 'softplus'}
           }
alpha_dict = {'model_name': 'NaiveEndogenousImpact',
              'parameter_set': {'activation': 'softplus'}
              }
kernel_para = np.ones((2, 1))
kernel_para[1, 0] = 0.5
kernel_dict = {'model_name': 'ExponentialKernel',
               'parameter_set': kernel_para}
loss_type = 'mle'
hawkes_model = HawkesProcessModel(num_type=num_type,
                                  mu_dict=mu_dict,
                                  alpha_dict=alpha_dict,
                                  kernel_dict=kernel_dict,
                                  activation='identity',
                                  loss_type=loss_type)

# initialize optimizer
optimizer = optim.Adam(hawkes_model.lambda_model.parameters(), lr=0.01)
scheduler = lr_scheduler.ExponentialLR(optimizer, gamma=0.8)

# train model
hawkes_model.fit(trainloader, optimizer, epochs, scheduler=scheduler,
                 sparsity=None, nonnegative=None, use_cuda=use_cuda, validation_set=validloader)
# save model
hawkes_model.save_model('{}/{}/full.pt'.format(util.POPPY_PATH, util.OUTPUT_DIR), mode='entire')
hawkes_model.save_model('{}/{}/para.pt'.format(util.POPPY_PATH, util.OUTPUT_DIR), mode='parameter')

# load model
hawkes_model.load_model('{}/{}/full.pt'.format(util.POPPY_PATH, util.OUTPUT_DIR), mode='entire')

# plot exogenous intensity
all_events = enumerate_all_events(database, seq_id=1, use_cuda=use_cuda)
hawkes_model.plot_exogenous(all_events,
                            output_name='{}/{}/exogenous_nonlinearHawkes.png'.format(util.POPPY_PATH, util.OUTPUT_DIR))

# plot endogenous Granger causality
hawkes_model.plot_causality(all_events,
                            output_name='{}/{}/causality_nonlinearHawkes.png'.format(util.POPPY_PATH, util.OUTPUT_DIR))

# simulate new data based on trained model
new_data, counts = hawkes_model.simulate(history=database,
                                         memory_size=memory_size,
                                         time_window=5,
                                         interval=1.0,
                                         max_number=10,
                                         use_cuda=use_cuda)
