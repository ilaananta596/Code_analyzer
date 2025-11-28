# Prompt Refinement Summary

## Problem
The initial prompt was too generic, causing the model to describe code rather than directly answer questions like "Who calls the validation logic?"

## Solution
Refined the prompt with question-specific guidance and clearer instructions.

## Key Improvements

### 1. Question Type Detection
The prompt now detects question types and provides specific guidance:
- **"Who calls" questions**: Direct instructions to list callers
- **"What does/How does" questions**: Instructions to explain functionality
- **"Where" questions**: Instructions to locate code

### 2. Clear Answer Format
For "who calls" questions, the prompt now:
- Explicitly instructs to start with "The following methods/files call [method name]:"
- Lists ALL callers from the "CALLED BY" sections
- Uses bullet points for clarity
- Avoids unnecessary code descriptions

### 3. Better Structure
- Clearer section headers
- Emphasis on "CALLED BY" information with ✓ marker
- More callers shown (up to 15 instead of 10)
- Filtered out operator calls for cleaner output

### 4. Answer Extraction
- Improved token extraction to get only newly generated text
- Better cleanup of model artifacts
- Handles chat template responses correctly

## Example Output

**Before:**
```
The `getLargestCC` method from the file... is called by the main function... 
It does not call any other methods directly mentioned...
```

**After:**
```
The following methods/files call `dice_coefficient`:
• comparisons/DeepLabV3+/infer_deeplabv3_res50_2D.py:<module>
• comparisons/DeepLabV3+/infer_deeplabv3_res50_3D.py:<module>
• comparisons/nnU-Net/infer_nnunet_2D.py:<module>
• comparisons/nnU-Net/infer_nnunet_3D.py:<module>
• utils/SurfaceDice.py:<module>
```

## Result
✅ Direct, clear answers
✅ Lists all relevant callers
✅ Easy to read format
✅ Focused on answering the question, not describing code

