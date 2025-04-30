(function($) {
    $(document).ready(function() {
        // Make sure we're on the stock item add/change page
        if ($("#id_item_name").length === 0 || $("#id_item_type").length === 0) {
            return;
        }
        
        console.log("StockItem form detected, initializing dynamic dropdowns");
        
        const itemNameField = $('#id_item_name');
        const itemTypeField = $('#id_item_type');
        
        // Define the options for each item name
        const typeOptions = {
            'Bottle': [
                ['0.5L', '0.5L'],
                ['1L', '1L'],
                ['1.5L', '1.5L'],
                ['2L', '2L'],
                ['5L', '5L'],
                ['10L', '10L'],
                ['20L', '20L'],
                ['20L Hard', '20L Hard (Reusable)']
            ],
            'Cap': [
                ['10/20L', '10/20L']
            ],
            'Label': [
                ['5L', '5L'],
                ['10L', '10L'],
                ['20L', '20L']
            ],
            'Shrink Wrap': [
                ['12x1L', '12x1L'],
                ['24x0.5L', '24x0.5L'],
                ['8x1.5L', '8x1.5L']
            ],
            'Water Bundle': [
                ['12x1L', '12x1L'],
                ['24x0.5L', '24x0.5L'],
                ['8x1.5L', '8x1.5L']
            ]
        };
        
        // Function to update item type options based on selected item name
        function updateItemTypeOptions() {
            const selectedName = itemNameField.val();
            console.log("Item name changed to:", selectedName);
            
            // Store current selection if any
            const currentSelection = itemTypeField.val();
            
            // Clear current options
            itemTypeField.empty();
            
            // Add placeholder option
            itemTypeField.append($('<option></option>')
                .attr('value', '')
                .text('---------'));
            
            // Update options for item type if we have options for this item name
            if (selectedName && typeOptions[selectedName]) {
                console.log("Loading options for:", selectedName);
                const options = typeOptions[selectedName];
                
                // Add new options
                options.forEach(function(option) {
                    itemTypeField.append($('<option></option>')
                        .attr('value', option[0])
                        .text(option[1]));
                });
                
                // Try to restore previous selection if it exists in new options
                if (currentSelection) {
                    itemTypeField.val(currentSelection);
                    // If the value couldn't be set (not in new options), reset to empty
                    if (itemTypeField.val() !== currentSelection) {
                        itemTypeField.val('');
                    }
                }
            }
        }
        
        // Update options when page loads
        updateItemTypeOptions();
        
        // Update options when item name changes
        itemNameField.on('change', updateItemTypeOptions);
        
        // Debug output to verify field access
        console.log("Initial item_name value:", itemNameField.val());
        console.log("Initial item_type value:", itemTypeField.val());
    });
})(django.jQuery);