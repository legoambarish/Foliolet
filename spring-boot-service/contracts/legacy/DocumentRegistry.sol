// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract DocumentRegistry {

    struct DocumentRecord {
        bytes32 documentHash;
        string caseId;
        address uploadedBy;
        uint256 timestamp;
        bool exists;
    }

    mapping(uint256 => DocumentRecord) private records;

    event DocumentStored(
        uint256 indexed documentId,
        bytes32 documentHash,
        string caseId,
        address indexed uploadedBy,
        uint256 timestamp
    );

    function storeDocumentHash(
        uint256 documentId,
        bytes32 documentHash,
        string calldata caseId
    ) external {
        require(!records[documentId].exists, "Document already recorded");

        records[documentId] = DocumentRecord({
            documentHash: documentHash,
            caseId: caseId,
            uploadedBy: msg.sender,
            timestamp: block.timestamp,
            exists: true
        });

        emit DocumentStored(documentId, documentHash, caseId, msg.sender, block.timestamp);
    }

    function getDocumentRecord(uint256 documentId)
        external
        view
        returns (bytes32 documentHash, string memory caseId, address uploadedBy, uint256 timestamp)
    {
        require(records[documentId].exists, "No record for this document");
        DocumentRecord storage record = records[documentId];
        return (record.documentHash, record.caseId, record.uploadedBy, record.timestamp);
    }

}
