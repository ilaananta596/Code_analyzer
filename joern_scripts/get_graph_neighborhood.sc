import io.shiftleft.semanticcpg.language._
import io.shiftleft.codepropertygraph.generated.nodes.Method
import io.shiftleft.codepropertygraph.generated.Operators

@main def main(cpgFile: String, methodName: String, filePath: String = "") = {
  // Load the CPG file
  loadCpg(cpgFile)
  
  // Find the method(s) - use exact same pattern as extract_methods.sc
  val allMethods = cpg.method.nameExact(methodName).l
  
  // Find matching method (with file filter if provided)
  val methodOpt = if (filePath.nonEmpty) {
    allMethods.find(m => m.file.name.headOption.getOrElse("") == filePath)
  } else {
    allMethods.headOption
  }
  
  if (methodOpt.isEmpty) {
    println(s"""{"methodName":"$methodName","filePath":"$filePath","found":false,"callers":[],"callees":[],"types":[]}""")
  } else {
    // Process using the same pattern as extract_methods.sc
    val result = List(methodOpt.get).map { m =>
      // Get callers: Find methods that contain calls to this method name
      // Search for calls where the code contains the method name (works for Python)
      // This finds methods that call the target method
      val callerMethods = try {
        val methodFullName = m.fullName
        val allCallers = cpg.method
          .where(_.call.code(s".*$methodName.*"))
          .fullName
          .l
          .distinct
          .map(fn => String.valueOf(fn))
        
        // Filter out the method itself (where it's defined)
        // Keep module-level callers as they represent actual call sites
        allCallers.filter(caller => caller != methodFullName)
      } catch {
        case _: Exception => List.empty[String]
      }
      
      // Get callees (methods called by this method) - use same pattern as extract_methods.sc line 78
      val callees = m.call.callee.name.l.distinct.map(n => String.valueOf(n))
      
      // Get types used in the method
      val types = m.ast.isIdentifier.typeFullName.l.distinct.filter(_.nonEmpty)
      
      val methodFilePath = m.file.name.headOption.getOrElse("")
      // Construct fullName from file and method name
      val methodFullName = methodFilePath + ":" + methodName
      
      (callerMethods, callees, types, methodFilePath, methodFullName)
    }.head
    
    val (callerMethods, callees, types, methodFilePath, methodFullName) = result
    
    // Build JSON - use same escape function as extract_methods.sc
    def escapeJson(s: String): String = {
      if (s == null) ""
      else s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    }
    
    // Build JSON arrays
    val callersJson = if (callerMethods.isEmpty) "[]" else {
      "[" + callerMethods.map(c => "\"" + escapeJson(c) + "\"").mkString(",") + "]"
    }
    
    val calleesJson = if (callees.isEmpty) "[]" else {
      "[" + callees.map(c => "\"" + escapeJson(c) + "\"").mkString(",") + "]"
    }
    
    val typesJson = if (types.isEmpty) "[]" else {
      "[" + types.map(t => "\"" + escapeJson(t) + "\"").mkString(",") + "]"
    }
    
    // Build final JSON
    val json = s"""{"methodName":"${escapeJson(methodName)}","filePath":"${escapeJson(methodFilePath)}","fullName":"${escapeJson(methodFullName)}","found":true,"callers":$callersJson,"callees":$calleesJson,"types":$typesJson}"""
    println(json)
  }
}
