import dynet as dy

from xnmt.serializer import Serializable
from xnmt.loss_calculator import LossCalculator, MLELoss
from xnmt.evaluator import LossScore
import xnmt.xnmt_evaluate

class EvalTask:
  '''
  An EvalTask is a task that does evaluation and returns one or more EvalScore objects.
  '''
  def eval(self):
    raise NotImplementedError("EvalTask.eval needs to be implemented in child classes")

class LossEvalTask(Serializable):
  '''
  A task that does evaluation of the loss function.
  '''

  yaml_tag = u'!LossEvalTask'
  
  def __init__(self, model, src_file, ref_file, loss_calculator=None):
    self.model = model
    self.loss_calculator = loss_calculator or LossCalculator(MLELoss())    
    self.src_file = src_file
    self.ref_file = ref_file
    self.src_data = None
    self.ref_data = None
    
  def eval(self):
    if self.src_data == None:
      self.src_data = list(self.model.src_reader.read_sents(self.src_file))
    if self.ref_data == None:
      self.ref_data = list(self.model.trg_reader.read_sents(self.ref_file))
    loss_val = 0
    ref_words_cnt = 0
    for src, trg in zip(self.src_data, self.ref_data):
      dy.renew_cg()
      standard_loss = self.model.calc_loss(src, trg, self.loss_calculator)
      ref_words_cnt += self.model.trg_reader.count_words(trg)
      loss_val += standard_loss.value()
    return LossScore(loss_val / ref_words_cnt)

class AccuracyEvalTask(Serializable):
  '''
  A task that does evaluation of some measure of accuracy.
  '''

  yaml_tag = u'!AccuracyEvalTask'

  def __init__(self, model, src_file, ref_file, hyp_file,
               eval_metrics="bleu", inference=None, candidate_id_file=None):
    self.model = model
    self.eval_metrics = map(lambda s: s.lower(), eval_metrics.split(","))
    self.src_file = src_file
    self.ref_file = ref_file
    self.hyp_file = hyp_file
    self.candidate_id_file = candidate_id_file
    self.inference = inference or self.model.inference
    print("****** MODEL {}, INFERENCE {}".format(self.model, self.inference))
    self.src_data = None
    self.ref_data = None
   
  def eval(self):
    self.inference(generator = self.model,
                   src_file = self.src_file,
                   trg_file = self.hyp_file,
                   candidate_id_file = self.candidate_id_file)
    # TODO: This is probably not ideal. Is there a cleaner way?
    evaluate_args = {}
    evaluate_args["hyp_file"] = self.hyp_file
    evaluate_args["ref_file"] = self.ref_file
    eval_scores = []
    for eval_metric in self.eval_metrics:
      evaluate_args["evaluator"] = eval_metric
      eval_scores.append(xnmt.xnmt_evaluate.xnmt_evaluate(**evaluate_args))
    return eval_scores
