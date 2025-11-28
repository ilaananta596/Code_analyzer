import io.shiftleft.semanticcpg.language._
import io.shiftleft.codepropertygraph.generated.nodes.Method
import io.shiftleft.codepropertygraph.generated.Operators

@main def main(cpgFile: String) = {
  // Load the CPG file
  loadCpg(cpgFile)
  
  val methods = cpg.method
    .filterNot(_.name.startsWith("<operator"))
    .filterNot(_.name.startsWith("<init"))
    .l
  
  def escapeJson(s: String): String = {
    if (s == null) ""
    else s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
  }
  
  def getMethodCode(m: Method): String = {
    // Try to get code from AST - get all statements and their code
    val statements = m.ast.isCall.code.l ++ m.ast.isIdentifier.code.l ++ m.ast.isLiteral.code.l
    if (statements.nonEmpty) {
      statements.mkString("\n")
    } else {
      // Fallback: try to get code property directly
      val codeStr = String.valueOf(m.code)
      if (codeStr != null && codeStr != "<empty>" && codeStr.nonEmpty) {
        codeStr
      } else {
        // Last resort: get method body AST nodes
        val bodyCode = m.ast.code.l.mkString("\n")
        if (bodyCode.nonEmpty) bodyCode else "<empty>"
      }
    }
  }
  
  def buildSignature(m: Method): String = {
    // Build Python-style signature from parameters
    val params = m.parameter.l
    if (params.isEmpty) {
      String.valueOf(m.signature) match {
        case s if s != null && s.nonEmpty => s
        case _ => ""
      }
    } else {
      val paramNames = params.map(p => String.valueOf(p.name)).filter(_ != "this")
      val paramTypes = params.map(p => String.valueOf(p.typeFullName))
      
      // Build signature: methodName(param1: type1, param2: type2, ...)
      val paramParts = paramNames.zip(paramTypes).map { case (name, tpe) =>
        if (tpe != null && tpe != "ANY" && tpe.nonEmpty) {
          s"$name: $tpe"
        } else {
          name
        }
      }
      
      s"${m.name}(${paramParts.mkString(", ")})"
    }
  }
  
  val methodList = methods.map { m =>
    // All properties are strings or can be converted to strings
    val methodName = escapeJson(String.valueOf(m.name))
    val fullName = escapeJson(String.valueOf(m.fullName))
    val signature = escapeJson(buildSignature(m))
    val filePath = escapeJson(m.file.name.headOption.getOrElse("unknown"))
    val lineNumber = m.lineNumber.headOption.getOrElse(0)
    
    // Get method code - try multiple approaches
    val code = escapeJson(getMethodCode(m))
    
    // Get parameter names for signature
    val paramNames = m.parameter.name.l.map(n => escapeJson(String.valueOf(n))).filter(_ != "this")
    val paramNamesJson = if (paramNames.isEmpty) "[]" else paramNames.map(n => s""""$n"""").mkString("[", ",", "]")
    
    // Get callees (methods called by this method)
    val callees = m.call.callee.name.l.distinct.map(n => escapeJson(String.valueOf(n)))
    val calleesJson = if (callees.isEmpty) "[]" else callees.map(c => s""""$c"""").mkString("[", ",", "]")
    
    // Get parameter types
    val paramTypes = m.parameter.typeFullName.l.map(t => escapeJson(String.valueOf(t)))
    val paramTypesJson = if (paramTypes.isEmpty) "[]" else paramTypes.map(t => s""""$t"""").mkString("[", ",", "]")
    
    s"""{"methodName":"$methodName","fullName":"$fullName","signature":"$signature","filePath":"$filePath","lineNumber":$lineNumber,"code":"$code","paramNames":$paramNamesJson,"callees":$calleesJson,"paramTypes":$paramTypesJson}"""
  }
  
  val methodsJson = if (methodList.isEmpty) "[]" else methodList.mkString("[", ",", "]")
  println(s"""{"methods":$methodsJson}""")
}
