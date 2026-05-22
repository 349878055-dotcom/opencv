/**
 * 新版 ComfyUI 把多行 STRING 画成「输入槽+文本框」，不读 Python 的 display_name。
 * 本扩展为节点 1 三个框补上左侧中文标签。
 */
import { app } from "/scripts/app.js";

const NODE_CLASS = "JintaoEye_NaturalLanguageIn";

const INPUT_LABELS = {
  system_prompt: "① 系统Prompt（留空=内置）",
  knowledge_base: "② 知识库（留空=通用内置）",
  customer_nl: "③ 客户自然语言（客户说什么）",
  use_prior_slider: "带上轮滑杆(修改用)",
  use_chatgpt: "用语言模型",
  chatgpt_model: "语言模型",
};

function applyNode1Labels(node) {
  if (!node || node.comfyClass !== NODE_CLASS) return;

  for (const inp of node.inputs ?? []) {
    const label = INPUT_LABELS[inp.name];
    if (!label) continue;
    inp.label = label;
    inp.localized_name = label;
  }

  for (const w of node.widgets ?? []) {
    const label = INPUT_LABELS[w.name];
    if (!label) continue;
    w.label = label;
    if (w.options && typeof w.options === "object") {
      w.options.label = label;
    }
  }

  if (typeof node.setSize === "function" && typeof node.computeSize === "function") {
    const sz = node.computeSize();
    if (sz?.[0] > node.size[0]) node.size[0] = sz[0];
    if (sz?.[1] > node.size[1]) node.size[1] = sz[1];
  }
  node.setDirtyCanvas?.(true, true);
}

function patchNodeType(nodeType, nodeData) {
  if (nodeData.name !== NODE_CLASS) return;

  const onNodeCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onNodeCreated?.apply(this, arguments);
    applyNode1Labels(this);
  };

  const onConfigure = nodeType.prototype.onConfigure;
  nodeType.prototype.onConfigure = function () {
    onConfigure?.apply(this, arguments);
    applyNode1Labels(this);
  };
}

app.registerExtension({
  name: "jintao.node_eye.node1_labels",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    patchNodeType(nodeType, nodeData);
  },
  async nodeCreated(node) {
    applyNode1Labels(node);
  },
  async loadedGraphNode(node) {
    applyNode1Labels(node);
  },
});
