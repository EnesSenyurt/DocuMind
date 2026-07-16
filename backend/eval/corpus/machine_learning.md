# Machine Learning Basics

## Gradient Descent

Gradient descent is an optimization algorithm that minimizes a loss function by
iteratively moving the model parameters in the direction of steepest descent.
At each step it computes the gradient of the loss with respect to the weights
and updates the weights by subtracting the gradient scaled by a learning rate.
A learning rate that is too large can overshoot the minimum, while one that is
too small makes training slow.

## Overfitting

Overfitting happens when a model learns the training data too closely, including
its noise, and therefore generalizes poorly to unseen data. Symptoms include a
low training error but a high validation error. Common remedies are collecting
more data, adding regularization such as L2 weight decay or dropout, and using
early stopping to halt training before the model memorizes the training set.

## Evaluation Metrics

Classification models are often evaluated with accuracy, precision, recall, and
the F1 score. For imbalanced datasets, accuracy alone is misleading, so the
precision-recall trade-off and the area under the ROC curve are preferred.
